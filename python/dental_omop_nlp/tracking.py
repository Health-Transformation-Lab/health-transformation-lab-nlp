"""MLflow tracking for every step that produces a number (docs/mlops.md).

    with track("13_reliability", "ai:tfidf_logreg", params={...}, simulated=True) as run:
        run.log_metrics({...}); run.log_artifact(path)

- Experiment: DENTAL_MLFLOW_EXPERIMENT (default "dental-omop-nlp"); on Databricks set
  it per target (the bundle creates one experiment per environment).
- Tracking store: MLFLOW_TRACKING_URI (Databricks: "databricks"; locally a sqlite
  file under mlruns/ is used if unset).
- Every run is tagged with the step, git commit, dataset fingerprint and whether
  it is simulated, so any number can be traced to the code and data that made it.
- No-op when mlflow isn't installed or DENTAL_MLFLOW=0, so scripts run without it.
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
import math
import os
import subprocess
from pathlib import Path

from .paths import DATASETS_DIR, REPO_ROOT
from .telemetry import traced

EXPERIMENT = "dental-omop-nlp"
log = logging.getLogger(__name__)


@traced
def enabled() -> bool:
    if os.environ.get("DENTAL_MLFLOW", "1") == "0":
        return False
    try:
        import mlflow  # noqa: F401
    except ImportError:
        return False
    return True


@traced
def git_commit() -> str:
    """Short commit of the code that's running: the deployed commit on Databricks (DENTAL_GIT_COMMIT, set by
    use_git_commit from the job), else asked of git, else "unknown"."""
    deployed = os.environ.get("DENTAL_GIT_COMMIT", "").strip()
    if deployed:
        return deployed[:7]
    try:
        return subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=10, check=False).stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001 - not a git checkout (e.g. a Databricks workspace copy)
        return "unknown"


@traced
def dataset_fingerprint(files: tuple[str, ...] = ("train.csv", "answer_key/review_key.csv")) -> str:
    h = hashlib.sha256()
    for f in files:
        p = DATASETS_DIR / f
        if p.exists():
            h.update(p.read_bytes())
    return h.hexdigest()[:12]


class _Run:
    def __init__(self, run_id=None):
        self.run_id = run_id

    @traced
    def log_metrics(self, m: dict):
        if self.run_id:
            import mlflow
            mlflow.log_metrics({k: float(v) for k, v in m.items() if v is not None and not math.isnan(float(v))})

    @traced
    def log_params(self, p: dict):
        if self.run_id:
            import mlflow
            mlflow.log_params({k: str(v)[:500] for k, v in p.items()})

    @traced
    def set_tags(self, t: dict):
        if self.run_id:
            import mlflow
            mlflow.set_tags({k: str(v) for k, v in t.items()})

    @traced
    def log_artifact(self, path):
        if self.run_id and Path(path).exists():
            import mlflow
            mlflow.log_artifact(str(path))


@traced
def use_git_commit(dbutils) -> str:
    """In a Databricks notebook: read the `git_commit` job parameter (the commit the bundle was deployed from)
    and hand it to this code and the scripts it starts. Returns it ("" when run by hand)."""
    dbutils.widgets.text("git_commit", "")
    commit = dbutils.widgets.get("git_commit").strip()
    if commit:
        os.environ["DENTAL_GIT_COMMIT"] = commit
    return commit


@traced
def pass_databricks_login() -> bool:
    """In a Databricks notebook: put its host and token in the environment so the scripts it starts (separate
    processes, without the notebook's login) can log to MLflow. Never raises; False if it couldn't."""
    try:
        from databricks.sdk import WorkspaceClient

        cfg = WorkspaceClient().config
        os.environ.setdefault("DATABRICKS_HOST", cfg.host)
        os.environ.setdefault("DATABRICKS_TOKEN", cfg.authenticate()["Authorization"].split(" ", 1)[1])
        return True
    except Exception as e:  # noqa: BLE001 - the scripts then run with tracking off (track() warns)
        log.warning("Databricks login not passed to scripts: %s", type(e).__name__)
        return False


def _setup():
    import mlflow
    if not os.environ.get("MLFLOW_TRACKING_URI"):
        (REPO_ROOT / "mlruns").mkdir(exist_ok=True)
        mlflow.set_tracking_uri(f"sqlite:///{REPO_ROOT / 'mlruns' / 'mlflow.db'}")
    mlflow.set_experiment(os.environ.get("DENTAL_MLFLOW_EXPERIMENT", EXPERIMENT))
    return mlflow


@contextlib.contextmanager
def track(step: str, run_name: str, params: dict | None = None, simulated: bool = False, nested: bool = False):
    if not enabled():
        yield _Run()
        return
    try:                    # tracking never fails a step: no store or no credentials -> run untracked
        mlflow = _setup()
        ctx = mlflow.start_run(run_name=run_name, nested=nested)
    except Exception as e:  # noqa: BLE001 - MlflowException, connection and auth errors alike
        log.warning("MLflow tracking off for %s: %s", run_name, str(e).splitlines()[0][:200])
        yield _Run()
        return
    with ctx as r:
        run = _Run(r.info.run_id)
        run.set_tags({"step": step, "git_commit": git_commit(), "dataset": dataset_fingerprint(),
                      "simulated": str(bool(simulated)).lower(), "project": "dental-omop-nlp", "data": "synthetic"})
        if params:
            run.log_params(params)
        yield run
