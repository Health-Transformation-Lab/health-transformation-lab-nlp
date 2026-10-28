"""Spec 018 US2: frames reach gold under the convention names; the declared gold model is what gets written."""
import importlib.util
import re
from pathlib import Path

import pandas as pd
import pytest

from dental_omop_nlp import gold_names, results_store

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("gold_model", ROOT / "diagrams" / "_build" / "gold_model.py")
gm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gm)


def declared(table):
    return [c.name for c in gm.TABLES[table].columns]


def csv(path):
    return pd.read_csv(ROOT / path)


@pytest.mark.parametrize("old,new", [("chart_answers", "fact_chart_answer"), ("judgments", "fact_judge_call"),
                                     ("judge_metrics", "judge_metric"), ("judge_agreement", "judge_agreement"),
                                     ("judge_run", "judge_cost")])
def test_each_judge_csv_twin_becomes_its_declared_gold_table(old, new):
    assert list(gold_names.to_gold(csv(f"data/datasets/judge/{old}.csv"), new).columns) == declared(new)


def test_deid_scores_with_their_group_become_deid_score():
    df = csv("data/deid/scores.csv").assign(group="x")
    assert list(gold_names.to_gold(df, "deid_score").columns) == declared("deid_score")


def test_load_results_frames_become_the_declared_result_tables(tmp_path):
    files = results_store.result_files(ROOT / "data" / "datasets").assign(git_commit="abc", loaded_at=pd.Timestamp.now())
    assert list(gold_names.to_gold(files, "dim_result_file").columns) == declared("dim_result_file")
    for kind in ("ai_predictions", "llm_details"):
        pd.DataFrame({"visit_id": [1], "pred": ["healthy"]}).to_csv(tmp_path / f"{kind}_m.csv", index=False)
    preds, _ = results_store.run_rows(tmp_path, "m", "databricks", "1", "abc", pd.Timestamp("2026-01-01"))
    assert list(gold_names.to_gold(preds.assign(loaded_at=pd.Timestamp.now()), "fact_prediction").columns) == declared(
        "fact_prediction")


def test_llm_details_with_their_provenance_become_fact_llm_call():
    d = csv("data/datasets/llm_details_medgemma-1.5-4b-it.csv").assign(
        method="m", sha256="0" * 64, source="databricks", run_id="1", run_ts=pd.Timestamp.now(), git_commit="abc",
        loaded_at=pd.Timestamp.now(), truth="healthy", difficulty="L1")
    assert list(gold_names.to_gold(d, "fact_llm_call").columns) == declared("fact_llm_call")


def test_a_column_the_mapping_does_not_know_fails_naming_it():
    with pytest.raises(ValueError, match="new_col"):
        gold_names.to_gold(pd.DataFrame({"visit_id": [1], "new_col": [2]}), "fact_prediction")


def test_counts_are_integers_in_gold():
    out = gold_names.to_gold(csv("data/datasets/judge/judge_run.csv"), "judge_cost")
    for c in [c for c in out.columns if c.endswith("_count")]:
        assert pd.api.types.is_integer_dtype(out[c]), c


def test_from_gold_gives_the_frame_back_for_the_judge_resume():
    j = csv("data/datasets/judge/judgments.csv")
    back = gold_names.from_gold(gold_names.to_gold(j, "fact_judge_call"), "fact_judge_call")
    pd.testing.assert_frame_equal(back, j, check_dtype=False)


def test_every_old_table_name_has_one_new_name():
    assert gold_names.RENAMED == {"result_files": "dim_result_file", "ai_predictions": "fact_prediction",
                                  "llm_reader_runs": "fact_llm_call", "chart_answers": "fact_chart_answer",
                                  "judgments": "fact_judge_call", "judge_metrics": "judge_metric",
                                  "judge_agreement": "judge_agreement", "judge_run": "judge_cost",
                                  "deid_scores": "deid_score"}
    assert set(gold_names.TABLES) == {n for n, t in gm.TABLES.items() if t.area != "file"}


def test_the_corpus_judge_sql_writes_the_declared_columns():
    sql = (ROOT / "databricks/notebooks/02_llm_judge.sql").read_text().lower()
    final = sql.split("from raw;")[0].rsplit("select", 1)[1]
    written = re.findall(r"\bas (\w+),?\s*$", final, re.MULTILINE)
    first = re.search(r"^\s+(\w+), (\w+), (\w+),", final, re.MULTILINE).groups()      # passed through, not aliased
    assert list(first) + written == declared("fact_corpus_judge_call")
    assert "'.fact_corpus_judge_call'" in sql and "'.judge_queue'" in sql
    for c in declared("judge_queue"):
        assert c in sql, c


def test_the_scorecard_dashboard_reads_only_declared_gold_columns():
    import json
    dash = json.loads((ROOT / "databricks/dashboards/scorecard.lvdash.json").read_text())
    keywords = {"select", "as", "from", "where", "round", "and", "left", "join", "on", "coalesce", "a", "s", "v",
                "dental_omop", "gold_dental_omop_perio", "status", "verdict", "correct", "all"}
    for ds in dash["datasets"]:
        sql = " ".join(ds["queryLines"]).lower()
        tables = set(re.findall(r"gold_dental_omop_perio\.(\w+)", sql))
        columns = {c for t in tables for c in declared(t)}
        aliases = set(re.findall(r"\bas `?(\w+)`?", sql))
        used = set(re.findall(r"\b[a-z_][a-z0-9_]*\b", re.sub(r"'[^']*'", "", sql))) - keywords - aliases - tables
        assert used <= columns, (ds["name"], used - columns)
