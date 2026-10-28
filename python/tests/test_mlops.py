"""MLflow tracking, MLflow GenAI judge, Unity Catalog-style registry with champion/challenger.
Runs against a throwaway local MLflow store (sqlite); no LLM or workspace needed."""

import importlib.util

import pandas as pd
import pytest

pytestmark = pytest.mark.skipif(importlib.util.find_spec("mlflow") is None, reason='pip install -e ".[track]"')

NOTE = "perio charting: BOP 40%, CAL 6 mm at #3.\nDx: generalized periodontitis stage III grade B."


@pytest.fixture
def store(tmp_path, monkeypatch):
    import mlflow
    uri = f"sqlite:///{tmp_path}/mlflow.db"
    monkeypatch.setenv("MLFLOW_TRACKING_URI", uri)
    monkeypatch.setenv("MLFLOW_REGISTRY_URI", uri)
    monkeypatch.setenv("DENTAL_MLFLOW", "1")
    monkeypatch.setenv("MLFLOW_DISABLE_AGENT_HINT", "1")
    mlflow.set_tracking_uri(uri)
    mlflow.set_registry_uri(uri)
    return uri


def test_tracking_logs_params_metrics_tags(store, tmp_path):
    import mlflow

    from health_transformation_lab_nlp.tracking import track
    f = tmp_path / "preds.csv"
    pd.DataFrame({"visit_id": [1], "pred": ["healthy"]}).to_csv(f, index=False)
    with track("unit", "tfidf_logreg", params={"rung": "tfidf_logreg"}, simulated=True) as run:
        run.log_metrics({"kappa": 0.7})
        run.log_artifact(f)
    r = mlflow.search_runs(experiment_names=["health-transformation-lab-nlp"], output_format="list")[0]
    assert r.data.params["rung"] == "tfidf_logreg" and r.data.metrics["kappa"] == 0.7
    assert r.data.tags["simulated"] == "true" and r.data.tags["step"] == "unit" and "git_commit" in r.data.tags


def test_tracking_is_a_noop_when_disabled(monkeypatch):
    from health_transformation_lab_nlp.tracking import track
    monkeypatch.setenv("DENTAL_MLFLOW", "0")
    with track("unit", "x") as run:
        run.log_metrics({"a": 1})       # nothing raised, nothing logged
    assert run.run_id is None


def test_mlflow_judge_definition_and_quote_gate():
    from health_transformation_lab_nlp.mlflow_judge import JUDGE_NAME, make_perio_judge, verdict_from_feedback
    j = make_perio_judge("databricks:/my-endpoint")
    assert j.name == JUDGE_NAME and "{{ inputs }}" in j.instructions and "{{ outputs }}" in j.instructions

    class FB:
        value, rationale = "correct", 'QUOTE: "Dx: generalized periodontitis stage III grade B." Stated stage III.'
    v = verdict_from_feedback(FB(), NOTE)
    assert v.verdict == "correct" and v.quote_ok

    class Bad:
        value, rationale = "correct", 'QUOTE: "stage IV" invented'
    assert not verdict_from_feedback(Bad(), NOTE).quote_ok


def test_mlflow_evaluate_with_simulated_judge(store):
    from health_transformation_lab_nlp.mlflow_judge import evaluate_predictions
    rows = pd.DataFrame({"visit_id": [1, 2, 3], "note": [NOTE] * 3,
                         "pred": ["periodontitis_stage_3", "healthy", "periodontitis_stage_3"],
                         "truth": ["periodontitis_stage_3", "periodontitis_stage_3", "periodontitis_stage_3"]})
    res = evaluate_predictions(rows, judge=None, method="sim:test", simulated=True)
    assert res["n"] == 3 and abs(res["metrics"]["agrees_with_reviewers/mean"] - 2 / 3) < 1e-9
    assert res["run_id"]


def test_register_load_and_promote_by_acceptance_test(store):
    from health_transformation_lab_nlp.model_registry import load_alias, log_and_register, promote_if_accepted
    from health_transformation_lab_nlp.registry import load_registry
    from health_transformation_lab_nlp.rungs import make_rung
    train = pd.DataFrame({"note_text": ["bop 40% no cal", "cal 6 mm stage iii", "healthy gums"] * 10,
                          "label": ["gingivitis", "periodontitis_stage_3", "healthy"] * 10})
    rung = make_rung("tfidf_logreg", load_registry()).fit(train)
    v1 = log_and_register(rung, "tfidf_logreg", "dental.perio_note_classifier", train.head(3), simulated=True)
    assert v1 == "1"
    m = load_alias("dental.perio_note_classifier", "challenger")
    assert list(m.predict(pd.DataFrame({"note_text": ["cal 6 mm stage iii"]}))) == ["periodontitis_stage_3"]
    vh = pd.DataFrame([{"rater": "ai:tfidf_logreg", "kind": "method", "verdict": "inferior", "diff_vs_human_bar": -0.2}])
    assert promote_if_accepted("dental.perio_note_classifier", v1, "ai:tfidf_logreg", vh) is False
    vh.loc[0, "verdict"] = "non-inferior"
    assert promote_if_accepted("dental.perio_note_classifier", v1, "ai:tfidf_logreg", vh) is True
    assert load_alias("dental.perio_note_classifier", "champion") is not None


def test_challenger_must_beat_current_champion(store):
    from health_transformation_lab_nlp.model_registry import log_and_register, promote_if_accepted
    from health_transformation_lab_nlp.registry import load_registry
    from health_transformation_lab_nlp.rungs import make_rung
    train = pd.DataFrame({"note_text": ["bop 40%", "cal 6 mm", "healthy"] * 10,
                          "label": ["gingivitis", "periodontitis_stage_3", "healthy"] * 10})
    rung = make_rung("tfidf_logreg", load_registry()).fit(train)
    name = "dental.m2"
    v1 = log_and_register(rung, "tfidf_logreg", name, train.head(3))
    v2 = log_and_register(rung, "tfidf_logreg", name, train.head(3))
    good = pd.DataFrame([{"rater": "m", "kind": "method", "verdict": "non-inferior", "diff_vs_human_bar": 0.05}])
    worse = good.assign(diff_vs_human_bar=0.01)
    assert promote_if_accepted(name, v1, "m", good) is True
    assert promote_if_accepted(name, v2, "m", worse) is False     # passes vs humans, but below champion


# --- Databricks built-in judges and production monitoring ---------------------------

def test_guidelines_judge_carries_the_aap_rules():
    from mlflow.genai.scorers import Guidelines

    from health_transformation_lab_nlp.mlflow_judge import GUIDELINES, make_guidelines_judge
    g = make_guidelines_judge("databricks:/my-endpoint")
    assert isinstance(g, Guidelines) and g.name == "aap_guidelines"
    text = " ".join(GUIDELINES)
    for rule in ("attachment loss", "five or more teeth", "gingivitis", "only what the note states"):
        assert rule in text


def test_phi_scorer_flags_identifiers_in_the_note():
    from health_transformation_lab_nlp.mlflow_judge import no_phi_in_note
    clean = no_phi_in_note(inputs={"note": NOTE})
    leaky = no_phi_in_note(inputs={"note": NOTE + "\nCall 404-555-0123 or jane.doe@example.com"})
    assert clean.value == "yes" and leaky.value == "no"


def test_evaluate_runs_extra_scorers(store):
    from health_transformation_lab_nlp.mlflow_judge import evaluate_predictions, no_phi_in_note
    rows = pd.DataFrame({"visit_id": [1, 2], "note": [NOTE] * 2,
                         "pred": ["periodontitis_stage_3"] * 2, "truth": ["periodontitis_stage_3"] * 2})
    res = evaluate_predictions(rows, judge=None, method="sim:test", simulated=True, extra_scorers=[no_phi_in_note])
    assert any(k.startswith("no_phi_in_note") for k in res["metrics"])


def test_monitoring_plan_samples_llm_judges_and_checks_every_trace():
    from health_transformation_lab_nlp.mlflow_judge import JUDGE_NAME, monitoring_plan
    plan = {name: rate for name, _, rate in monitoring_plan("databricks:/my-endpoint", sample_rate=0.1)}
    assert plan == {JUDGE_NAME: 0.1, "aap_guidelines": 0.1, "no_phi_in_note": 1.0}
    with pytest.raises(ValueError):
        monitoring_plan("databricks:/x", sample_rate=0)
