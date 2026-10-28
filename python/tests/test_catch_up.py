"""Databricks catches up by itself after an outage (issue #189): .github/scripts/catch_up.py decides, per target,
whether to wait, re-run the failed deploy, run Load results, or do nothing; .github/workflows/catch-up.yml runs it
on a schedule, in the deploy's concurrency group."""

import importlib.util
from datetime import datetime, timedelta, timezone

import pytest
import yaml

from health_transformation_lab_nlp.paths import REPO_ROOT

_spec = importlib.util.spec_from_file_location("catch_up", REPO_ROOT / ".github" / "scripts" / "catch_up.py")
cu = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cu)

WF = REPO_ROOT / ".github" / "workflows" / "catch-up.yml"
NOW = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)


def _deploy(conclusion="success", status="completed", hours_ago=2, attempt=1, sha="abc"):
    return {"run_id": 11, "status": status, "conclusion": conclusion, "attempt": attempt, "head_sha": sha,
            "created_at": NOW - timedelta(hours=hours_ago)}


def _load(deployed="abc", runs=()):
    """runs: (git_commit, life_cycle_state, result_state), newest first."""
    return {"job_id": 7, "deployed_commit": deployed,
            "runs": [{"git_commit": c, "life_cycle_state": lc, "result_state": rs} for c, lc, rs in runs]}


def _decide(reachable=True, deploy=None, load=None, down_hours=None):
    last = NOW - timedelta(hours=down_hours) if down_hours is not None else None
    return cu.decide(reachable, deploy, load, NOW, last)


# ---- Databricks down ---------------------------------------------------------------------------------------

def test_unreachable_with_a_failed_deploy_waits_for_the_next_check():
    d = _decide(reachable=False, deploy=_deploy("failure", hours_ago=3))
    assert d.action == "wait" and d.exit_code == 0 and d.severity == "SEV3"


def test_still_behind_after_a_day_fails_so_the_owner_hears():
    d = _decide(reachable=False, deploy=_deploy("failure", hours_ago=25))
    assert d.action == "wait" and d.exit_code == 1 and d.severity == "SEV2"


def test_unreachable_after_a_good_deploy_only_warns():
    d = _decide(reachable=False, deploy=_deploy("success"), down_hours=5)
    assert d.action == "wait" and d.exit_code == 0


def test_a_long_outage_escalates_even_after_a_good_deploy():
    # PR review: a good deploy, a failed --no-wait load, then days down must not stay a quiet warning
    for deploy in (_deploy("success"), None, _deploy(None, status="in_progress")):
        d = _decide(reachable=False, deploy=deploy, down_hours=30)
        assert d.exit_code == 1 and d.severity == "SEV2", deploy


@pytest.mark.parametrize("host,ok", [("https://adb-123.4.azuredatabricks.net", True),
                                     ("https://dbc-1a2b.cloud.databricks.com", True),
                                     ("adb-123.azuredatabricks.net", False), ("https://", False), ("", False),
                                     ("https://adb-1.azuredatabricks.net/", False)])
def test_the_host_is_checked_before_any_work(host, ok):
    assert (cu.check_host(host) is None) == ok


def test_when_databricks_last_answered_survives_between_checks(tmp_path):
    path = str(tmp_path / "s" / "dev.json")
    assert cu.read_last_reachable(path) is None
    cu.write_last_reachable(path, NOW)
    assert cu.read_last_reachable(path) == NOW


def test_a_rejected_credential_fails_at_once():
    d = _decide(reachable="auth", deploy=_deploy("failure", hours_ago=1))
    assert d.action == "fail" and d.exit_code == 1 and d.severity == "SEV2"
    assert "DATABRICKS_CLIENT_SECRET" in d.message


# ---- Databricks back: the deploy ---------------------------------------------------------------------------

def test_reachable_again_reruns_the_failed_deploy():
    d = _decide(deploy=_deploy("failure", hours_ago=20))
    assert d.action == "rerun_deploy" and d.exit_code == 0


def test_a_deploy_that_keeps_failing_while_reachable_is_not_an_outage():
    d = _decide(deploy=_deploy("failure", attempt=3))
    assert d.action == "fail" and d.exit_code == 1


def test_a_deploy_in_progress_is_left_alone():
    assert _decide(deploy=_deploy(None, status="in_progress")).action == "nothing"


def test_no_deploy_of_main_yet_is_nothing_to_do():
    assert _decide(deploy=None).action == "nothing"


# ---- Databricks back: Load results -------------------------------------------------------------------------

def test_deployed_but_never_loaded_runs_load_results():
    assert _decide(deploy=_deploy(), load=_load(runs=())).action == "run_load"


def test_loaded_an_older_commit_only_runs_load_results():
    d = _decide(deploy=_deploy(), load=_load(runs=[("old", "TERMINATED", "SUCCESS")]))
    assert d.action == "run_load"


def test_a_failed_load_of_this_commit_runs_it_again():
    d = _decide(deploy=_deploy(), load=_load(runs=[("abc", "INTERNAL_ERROR", "FAILED")]))
    assert d.action == "run_load"


def test_a_load_that_keeps_failing_fails_instead_of_retrying_forever():
    failed = [("abc", "TERMINATED", "FAILED")] * 3
    d = _decide(deploy=_deploy(), load=_load(runs=failed))
    assert d.action == "fail" and d.exit_code == 1


def test_a_load_in_progress_is_left_alone():
    assert _decide(deploy=_deploy(), load=_load(runs=[("abc", "RUNNING", None)])).action == "nothing"


def test_loaded_this_commit_is_nothing_to_do():
    assert _decide(deploy=_deploy(), load=_load(runs=[("abc", "TERMINATED", "SUCCESS")])).action == "nothing"


def test_no_load_results_job_in_the_workspace_is_nothing_to_do():
    assert _decide(deploy=_deploy(), load=None).action == "nothing"


# ---- reading the CLIs' answers -----------------------------------------------------------------------------

@pytest.mark.parametrize("stderr,expected", [
    ("Error: invalid_client: Client authentication failed", "auth"),
    ("Error: 401 Unauthorized", "auth"),
    ("Error: dial tcp: lookup adb-1.azuredatabricks.net: no such host", False),
    ("Error: 503 Service Unavailable", False),
])
def test_an_auth_error_is_told_apart_from_an_outage(stderr, expected):
    assert cu.classify_unreachable(stderr) == expected


def test_load_runs_are_read_from_either_cli_output_shape():
    run = {"state": {"life_cycle_state": "TERMINATED", "result_state": "SUCCESS"},
           "tasks": [{"task_key": "migrate_gold_names", "notebook_task": {"base_parameters": {"git_commit": "x"}}},
                     {"task_key": "load", "notebook_task": {"base_parameters": {"git_commit": "abc"}}}]}
    for out in ([run], {"runs": [run]}):
        assert cu.parse_runs(out) == [{"git_commit": "abc", "life_cycle_state": "TERMINATED",
                                       "result_state": "SUCCESS"}]


def test_the_deploy_job_for_the_target_is_found_in_the_newest_run_that_has_it():
    runs = [{"id": 2, "event": "workflow_dispatch", "status": "completed", "run_attempt": 1, "head_sha": "n",
             "created_at": "2026-10-29T10:00:00Z", "jobs": [{"name": "deploy (uat)", "status": "completed",
                                                             "conclusion": "success"}]},
            {"id": 1, "event": "push", "status": "completed", "run_attempt": 2, "head_sha": "m",
             "created_at": "2026-10-29T09:00:00Z", "jobs": [{"name": "deploy (dev)", "status": "completed",
                                                             "conclusion": "failure"}]}]
    runs[1]["jobs"][0]["id"] = 501
    d = cu.pick_deploy(runs, "dev")
    assert d["job_id"] == 501                     # re-run only this target's job, not uat's too
    assert d["run_id"] == 1 and d["conclusion"] == "failure" and d["attempt"] == 2 and d["head_sha"] == "m"
    assert d["created_at"] == datetime(2026, 10, 29, 9, tzinfo=timezone.utc)


# ---- the workflow ------------------------------------------------------------------------------------------

def test_workflow_runs_on_a_schedule_per_target_without_cancelling_a_queued_deploy():
    wf = yaml.safe_load(WF.read_text())
    on = wf.get("on", wf.get(True))
    assert on["schedule"] and "workflow_dispatch" in on
    job = wf["jobs"]["catch-up"]
    deploy = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "deploy.yml").read_text())["jobs"]["deploy"]
    # its own group: one shared with the deploy would cancel a deploy waiting in it (PR review)
    assert job["concurrency"]["group"] == "catch-up-${{ matrix.target }}" != deploy["concurrency"]["group"]
    assert job["environment"] == "${{ matrix.target }}"
    assert set(job["strategy"]["matrix"]["target"]) == {"dev", "uat"}
    assert wf["permissions"]["actions"] == "write"                          # to re-run the failed deploy
    text = WF.read_text()
    assert ".github/scripts/catch_up.py" in text and "./.github/actions/databricks-signin" in text
    assert "actions/cache/restore" in text and "actions/cache/save" in text and "CATCH_UP_STATE" in text
