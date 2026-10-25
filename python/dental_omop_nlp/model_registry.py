"""Models as MLflow pyfunc in Unity Catalog, with champion / challenger aliases (docs/mlops.md).

    v = log_and_register(rung, "tfidf_logreg", "dental_dev.dental.perio_note_classifier", example)
    promote_if_accepted("dental_dev.dental.perio_note_classifier", v, "ai:tfidf_logreg", agreement_vs_humans)
    model = load_alias("dental_dev.dental.perio_note_classifier", "champion")   # batch scoring / serving

- Any fitted rung (rules, TF-IDF, fusion, fine-tuned encoder) is wrapped as one pyfunc:
  input a DataFrame with note_text (and radiograph features for fusion), output a status.
- A new version gets the alias **challenger**. It becomes **champion** only if the
  acceptance test says non-inferior to the reviewers (reliability.agreement_vs_humans)
  **and** it is at least as close to the human bar as the current champion.
  The decision and its numbers are written as version tags.
- Registry: Unity Catalog on Databricks (`mlflow.set_registry_uri("databricks-uc")`,
  three-level name catalog.schema.model); any MLflow registry locally.
"""

from __future__ import annotations

import math
import os
import pickle
import tempfile
from pathlib import Path

import pandas as pd


def _pyfunc_class():
    import mlflow

    class PerioRungModel(mlflow.pyfunc.PythonModel):
        def load_context(self, context):
            with open(context.artifacts["rung"], "rb") as f:
                self.rung = pickle.load(f)

        def predict(self, context, model_input: pd.DataFrame, params=None):
            pred, _ = self.rung.predict(model_input)
            return pd.Series(pred, name="status")

    return PerioRungModel


def _uc():
    import mlflow

    from .tracking import _setup
    _setup()                      # same tracking/registry store as every other script
    if os.environ.get("DATABRICKS_RUNTIME_VERSION") or os.environ.get("MLFLOW_REGISTRY_URI") == "databricks-uc":
        mlflow.set_registry_uri("databricks-uc")
    return mlflow


def log_and_register(rung, rung_id: str, model_name: str, input_example: pd.DataFrame,
                     simulated: bool = False) -> str:
    """Log the fitted rung as a pyfunc in the active (or a new) run and register a version.
    Returns the version number; the new version gets the alias 'challenger'."""
    mlflow = _uc()
    from mlflow.models import infer_signature

    from .tracking import _setup, dataset_fingerprint, git_commit
    _setup()
    cols = [c for c in input_example.columns if c != "label"]
    ex = input_example[cols].head(3)
    sig = infer_signature(ex, pd.Series(rung.predict(ex)[0], name="status"))
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "rung.pkl"
        p.write_bytes(pickle.dumps(rung))
        active = mlflow.active_run()
        ctx = mlflow.start_run(run_name=f"register:{rung_id}") if active is None else _null()
        with ctx:
            mlflow.set_tags({"rung": rung_id, "git_commit": git_commit(), "dataset": dataset_fingerprint(),
                             "simulated": str(simulated).lower()})
            info = mlflow.pyfunc.log_model(name="model", python_model=_pyfunc_class()(), artifacts={"rung": str(p)},
                                           signature=sig, input_example=ex, registered_model_name=model_name)
    version = str(info.registered_model_version)
    client = mlflow.MlflowClient()
    client.set_registered_model_alias(model_name, "challenger", version)
    client.set_model_version_tag(model_name, version, "rung", rung_id)
    return version


class _null:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def promote_if_accepted(model_name: str, version: str, rater: str, agreement_vs_humans: pd.DataFrame) -> bool:
    """Champion only if the acceptance test is non-inferior for this model's predictions."""
    mlflow = _uc()
    client = mlflow.MlflowClient()
    row = agreement_vs_humans[agreement_vs_humans["rater"] == rater]
    verdict = row["verdict"].iloc[0] if len(row) else "missing"
    diff = row["diff_vs_human_bar"].iloc[0] if len(row) else float("nan")
    client.set_model_version_tag(model_name, version, "acceptance_verdict", str(verdict))
    client.set_model_version_tag(model_name, version, "acceptance_diff_vs_human_bar", f"{diff:.4f}")
    if verdict != "non-inferior":
        return False
    try:   # and at least as good as the current champion (Databricks MLOps guidance)
        champ = client.get_model_version_by_alias(model_name, "champion")
        champ_diff = float(champ.tags.get("acceptance_diff_vs_human_bar", "nan"))
        if champ.version != version and not math.isnan(champ_diff) and diff < champ_diff:
            client.set_model_version_tag(model_name, version, "promotion", f"below champion v{champ.version}")
            return False
    except Exception:  # noqa: BLE001, S110 - no champion yet: nothing to compare with
        pass
    client.set_registered_model_alias(model_name, "champion", version)
    client.set_model_version_tag(model_name, version, "promotion", "champion")
    return True


def load_alias(model_name: str, alias: str):
    mlflow = _uc()
    try:
        return mlflow.pyfunc.load_model(f"models:/{model_name}@{alias}")
    except Exception:  # noqa: BLE001 - alias not set yet
        return None
