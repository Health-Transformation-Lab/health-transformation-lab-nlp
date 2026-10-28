"""Catch Databricks up after an outage (issue #189), for one bundle target. Run by .github/workflows/catch-up.yml.

A merge to main deploys the bundle and starts Load results (deploy.yml). If Databricks is down then, the deploy
fails and nothing is loaded; if Load results itself fails, nobody sees it (the deploy starts it with --no-wait).
This checks, every few hours:

  Databricks unreachable       wait for the next check (SEV3); still behind after 24 hours: fail (SEV2, the owner
                               is emailed). A rejected credential fails at once (SEV2).
  last deploy of main failed   re-run its failed jobs; the deploy starts Load results
  deployed, not loaded         Load results has no successful run for the deployed commit: run it, wait for it
  otherwise                    nothing

Load results only adds file versions it hasn't loaded (by SHA-256), so running it again is safe.

    TARGET=dev REPO=owner/name python .github/scripts/catch_up.py
needs the gh CLI (GH_TOKEN, actions: write) and the databricks CLI signed in (DATABRICKS_HOST, ...).
"""

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

BEHIND_LIMIT = timedelta(hours=24)   # unreachable this long with a failed deploy: SEV2
MAX_DEPLOY_ATTEMPTS = 3              # failed this often while Databricks answers: a real failure, not an outage
MAX_LOAD_FAILURES = 3                # Load results failed this often for one commit: stop retrying
LOAD_JOB_NAME = "Load results"
RUNNING = {"PENDING", "QUEUED", "RUNNING", "TERMINATING", "BLOCKED", "WAITING_FOR_RETRY"}
_AUTH = re.compile(r"invalid_client|unauthori[sz]ed|unauthenticated|\b401\b|\b403\b|permission denied|"
                   r"invalid.*token|token.*expired", re.IGNORECASE)


@dataclass
class Decision:
    action: str          # nothing | wait | rerun_deploy | run_load | fail
    message: str
    exit_code: int = 0
    severity: str = ""   # AGENTS.md "Alerts and severity"


def decide(reachable, deploy: dict | None, load: dict | None, now: datetime) -> Decision:
    """reachable: True, False (no answer) or "auth" (credential refused). deploy: the newest deploy of main for
    this target (pick_deploy). load: the Load results job's deployed commit and recent runs, or None."""
    if reachable == "auth":
        return Decision("fail", "Databricks refused the service principal's sign-in: renew DATABRICKS_CLIENT_SECRET "
                        "in this GitHub environment (ops/secrets_register.yaml).", 1, "SEV2")
    if deploy is None:
        return Decision("nothing", "No deploy of main for this target yet.")
    if deploy["status"] != "completed":
        return Decision("nothing", f"Deploy run {deploy['run_id']} is still {deploy['status']}.")
    failed = deploy["conclusion"] != "success"
    if reachable is False:
        if not failed:
            return Decision("wait", "Databricks is not answering; the last deploy succeeded, so nothing is waiting "
                            "on it but Load results can't be checked. Next check retries.", 0, "SEV3")
        behind = now - deploy["created_at"]
        if behind > BEHIND_LIMIT:
            return Decision("wait", f"Databricks has not answered for the {behind.total_seconds() / 3600:.0f} hours "
                            f"since deploy run {deploy['run_id']} failed; results are waiting in git.", 1, "SEV2")
        return Decision("wait", f"Databricks is not answering; deploy run {deploy['run_id']} failed "
                        f"{behind.total_seconds() / 3600:.1f} hours ago. Next check retries.", 0, "SEV3")
    if failed:
        if deploy["attempt"] >= MAX_DEPLOY_ATTEMPTS:
            return Decision("fail", f"Deploy run {deploy['run_id']} failed {deploy['attempt']} times while Databricks "
                            "answers: not an outage, read the run's log.", 1, "SEV2")
        return Decision("rerun_deploy", f"Databricks answers again: re-running the failed jobs of deploy run "
                        f"{deploy['run_id']} (attempt {deploy['attempt'] + 1}); it starts Load results.", 0, "SEV3")
    if load is None:
        return Decision("nothing", f"No '{LOAD_JOB_NAME}' job in this workspace.")
    mine = [r for r in load["runs"] if r["git_commit"] == load["deployed_commit"]]
    if load["runs"] and load["runs"][0]["life_cycle_state"] in RUNNING:
        return Decision("nothing", "Load results is running.")
    if any(r["result_state"] == "SUCCESS" for r in mine):
        return Decision("nothing", f"Load results ran for the deployed commit {load['deployed_commit'][:12]}.")
    failures = sum(r["result_state"] not in (None, "SUCCESS") or r["life_cycle_state"] == "INTERNAL_ERROR"
                   for r in mine)
    if failures >= MAX_LOAD_FAILURES:
        return Decision("fail", f"Load results failed {failures} times for commit {load['deployed_commit'][:12]}: "
                        "read the job's last run in Databricks.", 1, "SEV2")
    why = "failed" if failures else "has not run"
    return Decision("run_load", f"Load results {why} for the deployed commit {load['deployed_commit'][:12]}: "
                    "running it.", 0, "SEV3" if failures else "")


# ---- reading the CLIs --------------------------------------------------------------------------------------

def classify_unreachable(stderr: str):
    """A failed `databricks current-user me`: "auth" when the credential was refused, else False (no answer)."""
    return "auth" if _AUTH.search(stderr or "") else False


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def pick_deploy(runs: list[dict], target: str) -> dict | None:
    """The newest deploy run (newest first, each with its jobs) that has a job for this target."""
    for run in runs:
        job = next((j for j in run.get("jobs", []) if j["name"] == f"deploy ({target})"), None)
        if job:
            return {"run_id": run["id"], "status": job["status"], "conclusion": job.get("conclusion"),
                    "attempt": run.get("run_attempt", 1), "head_sha": run["head_sha"],
                    "created_at": _ts(run["created_at"])}
    return None


def parse_runs(out) -> list[dict]:
    """`databricks jobs list-runs --expand-tasks -o json` (a list, or {"runs": [...]}), newest first."""
    runs = out.get("runs", []) if isinstance(out, dict) else out or []
    parsed = []
    for r in runs:
        state = r.get("state", {})
        task = next((t for t in r.get("tasks", []) if t.get("task_key") == "load"), {})
        parsed.append({"git_commit": task.get("notebook_task", {}).get("base_parameters", {}).get("git_commit", ""),
                       "life_cycle_state": state.get("life_cycle_state"), "result_state": state.get("result_state")})
    return parsed


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if check and p.returncode:
        raise RuntimeError(f"{' '.join(cmd[:3])} failed: {p.stderr.strip()[:300]}")
    return p


def _json(cmd: list[str]):
    return json.loads(_run(cmd).stdout or "null")


def reachable() -> object:
    p = _run(["databricks", "current-user", "me", "-o", "json"], check=False)
    return True if p.returncode == 0 else classify_unreachable(p.stderr)


def deploy_runs(repo: str) -> list[dict]:
    runs = _json(["gh", "api", f"repos/{repo}/actions/workflows/deploy.yml/runs?branch=main&per_page=15"])
    out = []
    for run in runs.get("workflow_runs", []):
        if run["event"] not in ("push", "workflow_dispatch"):
            continue
        run["jobs"] = _json(["gh", "api", f"repos/{repo}/actions/runs/{run['id']}/jobs"]).get("jobs", [])
        out.append(run)
    return out


def load_state() -> dict | None:
    jobs = _json(["databricks", "jobs", "list", "--name", LOAD_JOB_NAME, "-o", "json"]) or []
    jobs = jobs.get("jobs", []) if isinstance(jobs, dict) else jobs
    job = next((j for j in jobs if j.get("settings", {}).get("tags", {}).get("project")
                == "health-transformation-lab-nlp"), None)
    if job is None:
        return None
    runs = _json(["databricks", "jobs", "list-runs", "--job-id", str(job["job_id"]), "--limit", "10",
                  "--expand-tasks", "-o", "json"])
    return {"job_id": job["job_id"], "deployed_commit": job["settings"]["tags"].get("git_commit", ""),
            "runs": parse_runs(runs)}


def run_load(job_id: int, timeout_s: int = 3600, sleep=time.sleep) -> str:
    """Start Load results and wait: its result_state (SUCCESS, FAILED, ...)."""
    run_id = _json(["databricks", "jobs", "run-now", str(job_id), "--no-wait", "-o", "json"])["run_id"]
    print(f"started Load results run {run_id}", flush=True)
    for _ in range(timeout_s // 30):
        state = _json(["databricks", "jobs", "get-run", str(run_id), "-o", "json"]).get("state", {})
        if state.get("life_cycle_state") not in RUNNING:
            return state.get("result_state") or state.get("life_cycle_state") or "UNKNOWN"
        sleep(30)
    return "TIMEDOUT"


def _say(d: Decision, target: str) -> None:
    level = {"SEV2": "error", "SEV3": "warning"}.get(d.severity, "notice")
    print(f"::{level}::{target}: {d.message}" + (f" ({d.severity})" if d.severity else ""))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(f"- **{target}**: {d.action}. {d.message}\n")


def main() -> int:
    target, repo = os.environ["TARGET"], os.environ["REPO"]
    ok = reachable()
    deploy = pick_deploy(deploy_runs(repo), target)
    needs_load = ok is True and deploy and deploy["status"] == "completed" and deploy["conclusion"] == "success"
    d = decide(ok, deploy, load_state() if needs_load else None, datetime.now(timezone.utc))
    _say(d, target)
    if d.action == "rerun_deploy":
        _run(["gh", "run", "rerun", str(deploy["run_id"]), "--failed", "-R", repo])
    elif d.action == "run_load":
        result = run_load(load_state()["job_id"])
        if result != "SUCCESS":
            _say(Decision("fail", f"Load results ended {result}: read its run in Databricks.", 1, "SEV2"), target)
            return 1
        _say(Decision("nothing", "Load results succeeded: Databricks has caught up."), target)
    return d.exit_code


if __name__ == "__main__":
    sys.exit(main())
