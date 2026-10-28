"""Spec 016: every model result reaches Databricks, wherever it ran (results_store, record_results.py)."""

import subprocess
import sys

import pandas as pd
import pytest

from dental_omop_nlp import results_store as rs
from dental_omop_nlp.paths import REPO_ROOT

RECORD = REPO_ROOT / "kaggle" / "record_results.py"


def _preds(path, n, method_pred="healthy"):
    pd.DataFrame({"visit_id": range(n), "pred": method_pred, "p_healthy": 0.9}).to_csv(path, index=False)


def _details(path, n):
    pd.DataFrame({"visit_id": range(n), "model": "m", "prompt_version": "reader-v2", "shots": 0,
                  "status": "healthy", "gate_ok": [True] * (n - 1) + [False], "fallback": [False] * (n - 1) + [True],
                  "pred": ["healthy"] * (n - 2) + ["gingivitis"] * 2}).to_csv(path, index=False)


@pytest.fixture
def datasets(tmp_path):
    d = tmp_path / "datasets"
    d.mkdir()
    _preds(d / "ai_predictions_tfidf_logreg.csv", 4)
    _preds(d / "ai_predictions_medgemma-x.csv", 4)
    _details(d / "llm_details_medgemma-x.csv", 4)
    _preds(d / "simulated_ai_predictions_medgemma-x.csv", 4)
    _details(d / "simulated_llm_details_medgemma-x.csv", 4)
    return d


# ---- US2: find, fingerprint and shape the rows

def test_result_files_lists_real_results_with_kind_method_hash_and_rows(datasets):
    f = rs.result_files(datasets)
    assert sorted(f.file) == ["ai_predictions_medgemma-x.csv", "ai_predictions_tfidf_logreg.csv",
                              "llm_details_medgemma-x.csv"]                # simulated files are never results
    row = f.set_index("file").loc["llm_details_medgemma-x.csv"]
    assert row["kind"] == "llm_details" and row["method"] == "medgemma-x" and row["rows"] == 4
    assert len(row["sha256"]) == 64
    assert set(f.source) == {"repo"}                                          # nothing in the manifest yet


def test_source_and_run_url_come_from_the_manifest(datasets):
    pd.DataFrame([{"file": "llm_details_medgemma-x.csv", "source": "kaggle", "run_url": "https://x/1",
                   "recorded_at": "2026-10-28T00:00:00Z"}]).to_csv(datasets / rs.MANIFEST, index=False)
    f = rs.result_files(datasets).set_index("file")
    assert f.loc["llm_details_medgemma-x.csv", "source"] == "kaggle"
    assert f.loc["llm_details_medgemma-x.csv", "run_url"] == "https://x/1"
    assert f.loc["ai_predictions_tfidf_logreg.csv", "source"] == "repo"


def test_prediction_rows_keep_method_pred_and_provenance_only(datasets):
    f = rs.result_files(datasets)
    p = rs.prediction_rows(f[f.kind == "predictions"], datasets)
    assert list(p.columns) == ["method", "visit_id", "pred", "sha256", "source"]
    assert len(p) == 8 and set(p.method) == {"tfidf_logreg", "medgemma-x"}


def test_detail_rows_keep_every_details_column_plus_provenance(datasets):
    f = rs.result_files(datasets)
    d = rs.detail_rows(f[f.kind == "llm_details"], datasets)
    assert {"visit_id", "status", "gate_ok", "pred", "method", "sha256", "source"} <= set(d.columns)
    assert len(d) == 4


def test_new_files_drops_versions_already_loaded(datasets):
    f = rs.result_files(datasets)
    loaded = {f.set_index("file").loc["ai_predictions_tfidf_logreg.csv", "sha256"]}
    assert "ai_predictions_tfidf_logreg.csv" not in set(rs.new_files(f, loaded).file)
    assert len(rs.new_files(f, set())) == 3
    _preds(datasets / "ai_predictions_tfidf_logreg.csv", 5)                 # changed file: a new version
    assert "ai_predictions_tfidf_logreg.csv" in set(rs.new_files(rs.result_files(datasets), loaded).file)


# ---- US3: MLflow metrics for one loaded LLM run

def test_llm_run_metrics(datasets):
    d = pd.read_csv(datasets / "llm_details_medgemma-x.csv")
    truth = pd.Series(["healthy"] * 4, index=range(4))
    m = rs.llm_run_metrics(d, truth)
    assert m == {"rows": 4, "gate_fail_rate": 0.25, "fallback_rate": 0.25, "agreement_with_key": 0.5}


# ---- US1: record a collected Kaggle run (kaggle/record_results.py)

def _record(src, dest, *extra):
    return subprocess.run([sys.executable, str(RECORD), "--from", str(src), "--to", str(dest),
                           "--run-url", "https://github.com/o/r/actions/runs/9", *extra],
                          capture_output=True, text=True, check=False)


def test_record_copies_real_results_and_writes_the_manifest(tmp_path, datasets):
    out = tmp_path / "kaggle_out"
    out.mkdir()
    _preds(out / "ai_predictions_medgemma-x.csv", 6)
    _details(out / "llm_details_medgemma-x.csv", 6)
    _preds(out / "simulated_ai_predictions_medgemma-x.csv", 6)
    r = _record(out, datasets, "--min-rows", "6")
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(pd.read_csv(datasets / "ai_predictions_medgemma-x.csv")) == 6
    assert len(pd.read_csv(datasets / "simulated_ai_predictions_medgemma-x.csv")) == 4    # untouched
    m = pd.read_csv(datasets / rs.MANIFEST)
    assert set(m.file) == {"ai_predictions_medgemma-x.csv", "llm_details_medgemma-x.csv"}
    assert set(m.source) == {"kaggle"} and set(m.run_url) == {"https://github.com/o/r/actions/runs/9"}
    r = _record(out, datasets, "--min-rows", "6")                             # recording again: one row per file
    assert len(pd.read_csv(datasets / rs.MANIFEST)) == 2


def test_record_refuses_a_smaller_run_and_changes_nothing(tmp_path, datasets):
    out = tmp_path / "kaggle_out"
    out.mkdir()
    _preds(out / "ai_predictions_medgemma-x.csv", 2)                          # a 2-note test run
    before = (datasets / "ai_predictions_medgemma-x.csv").read_bytes()
    r = _record(out, datasets)
    assert r.returncode == 3 and "fewer rows" in r.stdout
    assert (datasets / "ai_predictions_medgemma-x.csv").read_bytes() == before
    assert not (datasets / rs.MANIFEST).exists()


def test_record_refuses_a_test_run_of_a_new_method(tmp_path, datasets):
    # a 10-note run with shots=2 is named ...+k2: no committed file to compare with, so the full-run size decides
    out = tmp_path / "kaggle_out"
    out.mkdir()
    _preds(out / "ai_predictions_medgemma-x+k2.csv", 3)
    r = _record(out, datasets, "--min-rows", "4")
    assert r.returncode == 3 and "fewer rows" in r.stdout
    assert not (datasets / "ai_predictions_medgemma-x+k2.csv").exists()


def test_record_defaults_to_the_full_review_set():
    import importlib.util

    from dental_omop_nlp.paths import DATASETS_DIR
    spec = importlib.util.spec_from_file_location("record_results", RECORD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.full_run_rows() == len(pd.read_csv(DATASETS_DIR / "answer_key" / "review_key.csv")) == 240


def test_record_with_no_results_says_so(tmp_path, datasets):
    out = tmp_path / "empty"
    out.mkdir()
    r = _record(out, datasets)
    assert r.returncode == 3 and "no result files" in r.stdout


# ---- workflows, job and notebooks

def _text(rel):
    return (REPO_ROOT / rel).read_text()


def test_kaggle_workflow_opens_a_pr_with_the_results():
    import yaml
    wf = yaml.safe_load(_text(".github/workflows/kaggle-medgemma.yml"))
    on = wf.get("on", wf.get(True))
    assert "open_pr" in on["workflow_dispatch"]["inputs"]
    perms = wf["jobs"]["run"]["permissions"]
    assert perms["contents"] == "write" and perms["pull-requests"] == "write"
    text = _text(".github/workflows/kaggle-medgemma.yml")
    assert "kaggle/record_results.py" in text and "gh pr create" in text
    step = next(s for s in wf["jobs"]["run"]["steps"] if "record_results.py" in s.get("run", ""))
    run = step["run"]
    assert run.index("pip install") < run.index("record_results.py")   # it needs pandas and the package
    assert "!cancelled()" in text and "always() && inputs.open_pr" not in text   # a cancelled run commits nothing


def test_load_results_job_runs_the_notebook_with_the_bundle_schema():
    import yaml
    jobs = yaml.safe_load(_text("databricks/resources/jobs.yml"))["resources"]["jobs"]
    task = jobs["load_results"]["tasks"][0]["notebook_task"]
    assert task["notebook_path"] == "../notebooks/10_load_results.py"
    p = task["base_parameters"]
    assert p["catalog"] == "${resources.schemas.gold.catalog_name}" and p["schema"] == "${resources.schemas.gold.name}"
    assert p["git_commit"] == "${bundle.git.commit}"


def test_deploy_starts_load_results_without_waiting():
    text = _text(".github/workflows/deploy.yml")
    assert "bundle run -t \"$TARGET\" --no-wait load_results" in text


def test_load_notebook_appends_new_versions_to_the_three_tables():
    nb = _text("databricks/notebooks/10_load_results.py")
    for t in ("result_files", "ai_predictions", "llm_reader_runs"):
        assert f'"{t}"' in nb, t
    assert "new_files(" in nb and 'mode("append")' in nb and "mergeSchema" in nb
    assert "DELETE FROM" in nb            # a load that failed partway is redone, not duplicated
    assert "tracking.track(" in nb and "llm_run_metrics(" in nb


def test_reader_job_tags_its_rows_as_databricks():
    assert 'source="databricks"' in _text("databricks/notebooks/03_medgemma_reader.py")
