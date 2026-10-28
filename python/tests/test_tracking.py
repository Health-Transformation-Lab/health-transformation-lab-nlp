"""Tracking must never fail a pipeline step (tracking.py)."""

import logging

import pytest

from dental_omop_nlp import tracking


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
    from dental_omop_nlp.paths import REPO_ROOT
    for nb in ("03_medgemma_reader.py", "08_encoder_gpu.py"):
        assert "tracking.pass_databricks_login()" in (REPO_ROOT / "databricks" / "notebooks" / nb).read_text(), nb
