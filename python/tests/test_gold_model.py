"""The gold ERDs are drawn from diagrams/_build/gold_model.py: its columns must be the tables' columns."""
import importlib.util
from pathlib import Path

import pandas as pd

from dental_omop_nlp import results_store

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("gold_model", ROOT / "diagrams" / "_build" / "gold_model.py")
gm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gm)


def cols(table):
    return [c.name for c in gm.TABLES[table].columns]


def header(path):
    return list(pd.read_csv(ROOT / path, nrows=0).columns)


def test_the_model_declares_the_nine_gold_tables():
    gold = {n for n, t in gm.TABLES.items() if t.area != "file"}
    assert gold == {"result_files", "ai_predictions", "llm_reader_runs", "chart_answers", "judgments",
                    "judge_metrics", "judge_agreement", "judge_run", "deid_scores"}


def test_judge_scorecard_tables_have_their_csv_twins_columns_in_order():
    for t in ("chart_answers", "judgments", "judge_metrics", "judge_agreement", "judge_run"):
        assert cols(t) == header(f"data/datasets/judge/{t}.csv"), t


def test_deid_scores_is_the_scores_csv_plus_its_group():
    assert cols("deid_scores") == header("data/deid/scores.csv") + ["group"]


def test_result_files_is_what_load_results_writes():
    assert cols("result_files") == list(results_store.result_files(ROOT / "data" / "datasets").columns) + [
        "git_commit", "loaded_at"]


def test_ai_predictions_holds_the_reader_jobs_columns_and_load_results_load_time(tmp_path):
    for kind in ("ai_predictions", "llm_details"):
        pd.DataFrame({"visit_id": [1], "pred": ["healthy"]}).to_csv(tmp_path / f"{kind}_m.csv", index=False)
    preds, _ = results_store.run_rows(tmp_path, "m", "databricks", "1", "abc", pd.Timestamp("2026-01-01"))
    assert cols("ai_predictions") == list(preds.columns) + ["loaded_at"]


def test_llm_reader_runs_holds_every_llm_details_column_and_the_provenance():
    for path in sorted((ROOT / "data" / "datasets").glob("*llm_details_*.csv")):
        details = header(path)
        assert cols("llm_reader_runs")[:len(details)] == details, path.name
    assert set(cols("llm_reader_runs")[len(details):]) == {"method", "sha256", "source", "run_id", "run_ts",
                                                          "git_commit", "loaded_at", "truth", "difficulty"}


def test_every_relationship_joins_declared_columns():
    for r in gm.RELATIONSHIPS:
        for table, columns in ((r.parent, r.parent_cols), (r.child, r.child_cols)):
            assert set(columns) <= set(cols(table)), (r, table)


def test_every_column_says_what_it_is():
    for name, t in gm.TABLES.items():
        assert t.description, name
        for c in t.columns:
            assert c.type and c.description, (name, c.name)
