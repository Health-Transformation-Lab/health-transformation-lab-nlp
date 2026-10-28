"""Tracking must never fail a pipeline step (tracking.py)."""

import logging

import pytest

from health_transformation_lab_nlp import tracking


def test_tracking_never_fails_the_step_when_mlflow_cannot_connect(monkeypatch, caplog):
    """MedGemma in dev: the predictions were written, then the script died because MLflow had no Databricks
    credentials in the subprocess ("Reading Databricks credential configuration failed"). Tracking that
    can't start warns and runs the step without it; errors in the step itself still raise."""
    def broken():
        raise RuntimeError("Reading Databricks credential configuration failed")

    monkeypatch.setattr(tracking, "enabled", lambda: True)
    monkeypatch.setattr(tracking, "_setup", broken)
    ran = []
    with caplog.at_level(logging.WARNING), tracking.track("unit", "x") as run:
        run.log_metrics({"a": 1})
        ran.append(True)
    assert ran and run.run_id is None
    assert "tracking off" in caplog.text and "credential" in caplog.text
    with pytest.raises(ValueError), tracking.track("unit", "x"):
        raise ValueError("a real failure in the step")


def test_notebook_login_is_passed_to_the_scripts_it_runs(monkeypatch):
    """Scripts started from a Databricks notebook are separate processes without its login, so MLflow there
    can't reach the workspace. The notebook passes host and token on through the environment."""
    import sys
    import types

    class Cfg:
        host = "https://example.cloud.databricks.com"

        def authenticate(self):
            return {"Authorization": "Bearer abc"}

    sdk = types.ModuleType("databricks.sdk")
    sdk.WorkspaceClient = lambda: types.SimpleNamespace(config=Cfg())
    monkeypatch.setitem(sys.modules, "databricks", types.ModuleType("databricks"))
    monkeypatch.setitem(sys.modules, "databricks.sdk", sdk)
    monkeypatch.delenv("DATABRICKS_HOST", raising=False)
    monkeypatch.delenv("DATABRICKS_TOKEN", raising=False)
    assert tracking.pass_databricks_login() is True
    import os
    assert os.environ["DATABRICKS_HOST"] == Cfg.host and os.environ["DATABRICKS_TOKEN"] == "abc"


def test_passing_the_login_never_fails(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "databricks.sdk", None)          # not installed
    assert tracking.pass_databricks_login() is False


def test_gpu_notebooks_pass_their_login_to_the_scripts():
    from health_transformation_lab_nlp.paths import REPO_ROOT
    for nb in ("03_medgemma_reader.py", "08_encoder_gpu.py"):
        assert "tracking.pass_databricks_login()" in (REPO_ROOT / "databricks" / "notebooks" / nb).read_text(), nb


def test_git_commit_comes_from_the_deploy_when_the_code_is_not_a_git_checkout(monkeypatch):
    """On Databricks the bundle's files aren't a git checkout, so MLflow tagged every run "unknown".
    The deployed commit is handed in as DENTAL_GIT_COMMIT and wins over asking git."""
    monkeypatch.setenv("DENTAL_GIT_COMMIT", "f00dfeed0123456789abcdef0123456789abcdef")
    assert tracking.git_commit() == "f00dfee"
    monkeypatch.setenv("DENTAL_GIT_COMMIT", "  ")
    assert tracking.git_commit() != ""                                 # blank: falls back to git / "unknown"


def test_notebook_hands_the_deployed_commit_to_the_code(monkeypatch):
    import os

    class Widgets:
        def __init__(self):
            self.values = {"git_commit": "abc1234def"}

        def text(self, name, default):
            self.values.setdefault(name, default)

        def get(self, name):
            return self.values[name]

    class DBUtils:
        widgets = Widgets()

    monkeypatch.delenv("DENTAL_GIT_COMMIT", raising=False)
    assert tracking.use_git_commit(DBUtils()) == "abc1234def"
    assert os.environ["DENTAL_GIT_COMMIT"] == "abc1234def" and tracking.git_commit() == "abc1234"


# ---- the MedGemma reader job: 'For input string: "None"' in its log; tracking must check its settings first

class _FakeMlflow:
    """Stands in for mlflow: records calls; log_metrics can be made to fail like the Databricks server does."""
    def __init__(self, fail_on=None):
        import types
        self.calls, self.fail_on = [], fail_on
        self.module = types.ModuleType("mlflow")
        for name in ("set_tracking_uri", "set_experiment", "log_params", "set_tags", "log_metrics", "log_artifact"):
            setattr(self.module, name, self._recorder(name))
        self.module.start_run = self.start_run

    def _recorder(self, name):
        def call(*a, **kw):
            self.calls.append(name)
            if name == self.fail_on:
                raise RuntimeError('INVALID_PARAMETER_VALUE: For input string: "None"')
        return call

    def start_run(self, **kw):
        import contextlib
        import types
        self.calls.append("start_run")
        return contextlib.nullcontext(types.SimpleNamespace(info=types.SimpleNamespace(run_id="r1")))


def _with_mlflow(monkeypatch, fake):
    import sys
    monkeypatch.setitem(sys.modules, "mlflow", fake.module)
    monkeypatch.delenv("DENTAL_MLFLOW", raising=False)


def test_on_databricks_the_experiment_must_be_an_absolute_path(monkeypatch, caplog):
    fake = _FakeMlflow()
    _with_mlflow(monkeypatch, fake)
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "databricks")
    monkeypatch.delenv("DENTAL_MLFLOW_EXPERIMENT", raising=False)
    with caplog.at_level(logging.WARNING), tracking.track("unit", "x") as run:
        pass
    assert run.run_id is None and "start_run" not in fake.calls
    assert "DENTAL_MLFLOW_EXPERIMENT" in caplog.text and "absolute" in caplog.text


def test_on_databricks_the_bundle_experiment_is_used(monkeypatch):
    fake = _FakeMlflow()
    _with_mlflow(monkeypatch, fake)
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "databricks")
    monkeypatch.setenv("DENTAL_MLFLOW_EXPERIMENT", "/Workspace/Users/x/.bundle/dental/dev/health-transformation-lab-nlp-experiment")
    with tracking.track("unit", "x", params={"shots": None}) as run:
        run.log_metrics({"a": 1.0})
    assert run.run_id == "r1" and "log_metrics" in fake.calls


def test_a_logging_error_never_fails_the_step(monkeypatch, caplog):
    fake = _FakeMlflow(fail_on="log_metrics")
    _with_mlflow(monkeypatch, fake)
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "databricks")
    monkeypatch.setenv("DENTAL_MLFLOW_EXPERIMENT", "/Shared/dental")
    ran = []
    with caplog.at_level(logging.WARNING), tracking.track("unit", "x") as run:
        run.log_metrics({"a": 1.0})
        ran.append(True)
    assert ran and 'For input string' in caplog.text


def test_reader_job_logs_to_the_bundle_experiment():
    import yaml

    from health_transformation_lab_nlp.paths import REPO_ROOT
    nb = (REPO_ROOT / "databricks" / "notebooks" / "03_medgemma_reader.py").read_text()
    assert 'os.environ["MLFLOW_TRACKING_URI"] = "databricks"' in nb
    assert 'os.environ["DENTAL_MLFLOW_EXPERIMENT"]' in nb
    assert nb.index('os.environ["DENTAL_MLFLOW_EXPERIMENT"]') < nb.index("11_ai_predict.py")
    jobs = yaml.safe_load((REPO_ROOT / "databricks" / "resources" / "jobs.yml").read_text())
    params = jobs["resources"]["jobs"]["medgemma_reader"]["tasks"][0]["notebook_task"]["base_parameters"]
    assert params["experiment_name"] == "${resources.experiments.dental_experiment.name}"
    assert params["run_id"] == "{{job.run_id}}"          # the batch key: the same for every retry of a run


def test_a_logging_warning_keeps_the_root_cause(monkeypatch, caplog):
    # MedGemma reader on serverless GPU: log_artifact failed with urllib3's "Max retries exceeded with url: <long
    # path> (Caused by ...)"; cutting the message at 200 characters dropped the cause, the part that says why
    fake = _FakeMlflow(fail_on="log_artifact")
    msg = ("HTTPSConnectionPool(host='us-east-2.storage.cloud.databricks.com', port=443): Max retries exceeded with "
           "url: /api/2.0/fs/files/WorkspaceInternal/Jobs/mlflow-tracking/1/" + "a" * 300 + "/x.csv "
           "(Caused by NameResolutionError: Failed to resolve 'us-east-2.storage.cloud.databricks.com')")

    def fail(*a, **kw):
        raise RuntimeError(msg)

    fake.module.log_artifact = fail
    _with_mlflow(monkeypatch, fake)
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "databricks")
    monkeypatch.setenv("DENTAL_MLFLOW_EXPERIMENT", "/Shared/dental")
    with caplog.at_level(logging.WARNING), tracking.track("unit", "x") as run:
        run.log_artifact(__file__)
    assert "us-east-2.storage.cloud.databricks.com" in caplog.text           # where
    assert "Caused by NameResolutionError" in caplog.text                    # why
    assert len(caplog.records[-1].getMessage()) < 600                         # still one readable line
