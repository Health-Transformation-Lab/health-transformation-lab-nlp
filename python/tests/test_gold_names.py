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


def test_every_llm_details_file_with_its_provenance_becomes_fact_llm_call():
    for path in sorted((ROOT / "data" / "datasets").glob("*llm_details_*.csv")):
        d = pd.read_csv(path).assign(
            method="m", sha256="0" * 64, source="databricks", run_id="1", run_ts=pd.Timestamp.now(), git_commit="abc",
            loaded_at=pd.Timestamp.now(), truth="healthy", difficulty="L1")
        assert list(gold_names.to_gold(d, "fact_llm_call").columns) == declared("fact_llm_call"), path.name


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


def dashboard_columns_not_declared(dash):
    """Per dataset: names its queries read (string literals and the alias after each AS left out) that no table
    it reads declares."""
    keywords = {"select", "as", "from", "where", "round", "and", "left", "join", "on", "coalesce",
                "dental_omop", "gold_dental_omop_perio"}
    out = {}
    for ds in dash["datasets"]:
        sql = " ".join(ds["queryLines"]).lower()
        tables = set(re.findall(r"gold_dental_omop_perio\.(\w+)", sql))
        table_aliases = set(re.findall(r"gold_dental_omop_perio\.\w+ (\w+)", sql))
        columns = {c for t in tables for c in declared(t)}
        sql = re.sub(r"\bas\s+`?\w+`?", " ", re.sub(r"'[^']*'", " ", sql))
        used = set(re.findall(r"\b[a-z_][a-z0-9_]*\b", sql)) - keywords - tables - table_aliases
        out[ds["name"]] = used - columns
    return out


def test_the_scorecard_dashboard_reads_only_declared_gold_columns():
    import json
    dash = json.loads((ROOT / "databricks/dashboards/scorecard.lvdash.json").read_text())
    assert all(not v for v in dashboard_columns_not_declared(dash).values()), dashboard_columns_not_declared(dash)


def test_the_dashboard_check_catches_an_old_column_kept_under_its_old_alias():
    dash = {"datasets": [{"name": "x", "queryLines": [
        "SELECT ROUND(100 * difference, 1) AS `difference`, kappa AS kappa FROM dental_omop.gold_dental_omop_perio.judge_metric"]}]}
    assert dashboard_columns_not_declared(dash)["x"] == {"difference", "kappa"}


# spec 018 US2 migration: what 11_migrate_gold_names.py does with each old table, given the tables that exist
# (name -> columns). Actions: copy (new table absent), merge (new table exists: add old rows whose batch key it
# lacks), rewrite (same name, old columns), stale (new table exists and is rebuilt each run), fail (unknown columns).

def _cols(analysis_table):
    return list(gold_names.TABLES[analysis_table])


def test_an_old_table_with_no_new_one_is_copied():
    plan = gold_names.migration_plan({"ai_predictions": _cols("fact_prediction")})
    assert plan == [("copy", "ai_predictions", "fact_prediction")]


def test_nothing_to_do_once_the_old_tables_are_gone():
    assert gold_names.migration_plan({"fact_prediction": declared("fact_prediction")}) == []


def test_a_new_table_written_first_gets_the_old_rows_merged_in_not_lost():
    plan = gold_names.migration_plan({"ai_predictions": _cols("fact_prediction"),
                                      "fact_prediction": declared("fact_prediction")})
    assert plan == [("merge", "ai_predictions", "fact_prediction")]


def test_a_summary_table_rebuilt_since_is_left_as_stale():
    plan = gold_names.migration_plan({"judge_metrics": _cols("judge_metric"), "judge_metric": declared("judge_metric")})
    assert plan == [("stale", "judge_metrics", "judge_metric")]


def test_judgments_written_by_the_corpus_judge_go_to_the_corpus_table():
    plan = gold_names.migration_plan({"judgments": _cols("fact_corpus_judge_call")})
    assert plan == [("copy", "judgments", "fact_corpus_judge_call")]


def test_judgments_written_by_the_scorecard_go_to_fact_judge_call():
    plan = gold_names.migration_plan({"judgments": _cols("fact_judge_call")})
    assert plan == [("copy", "judgments", "fact_judge_call")]


def test_judge_agreement_is_rewritten_in_place_until_it_has_the_gold_columns():
    assert gold_names.migration_plan({"judge_agreement": _cols("judge_agreement")}) == [
        ("rewrite", "judge_agreement", "judge_agreement")]
    assert gold_names.migration_plan({"judge_agreement": declared("judge_agreement")}) == []


def test_an_old_table_with_a_column_no_mapping_knows_fails_naming_it():
    plan = gold_names.migration_plan({"deid_scores": _cols("deid_score") + ["mystery"]})
    assert plan == [("fail", "deid_scores", "mystery")]


def test_every_mergeable_table_has_a_batch_key_of_gold_columns():
    for table, key in gold_names.MERGE_KEYS.items():
        assert set(key) <= set(declared(table)), table


def test_the_migration_notebook_follows_the_plan_and_checks_row_counts():
    nb = (ROOT / "databricks/notebooks/11_migrate_gold_names.py").read_text()
    assert "gold_names.migration_plan(" in nb and "gold_names.MERGE_KEYS" in nb
    assert "localCheckpoint" not in nb                 # not certain on serverless; Delta overwrite reads a snapshot
    assert "row counts differ" in nb                   # a copy that lost rows fails
    assert 'spark.sql(f"DROP' not in nb                # prints the drops, never runs them


def test_the_scorecard_waits_for_the_migration_so_it_never_pays_for_calls_it_has():
    nb = (ROOT / "databricks/notebooks/07_judge_scorecard.py").read_text()
    assert "gold_names.migration_plan(" in nb and "run Load results first" in nb
