"""Spec 019: the tables the two graders read, built from the committed CSVs (US1 data quality, US3 lab grader)."""

import pytest

from dental_omop_nlp import grader_tables as gt
from dental_omop_nlp.paths import DATASETS_DIR

DQ = {
    "dq_checks": {"check_name", "category", "clinic", "n_checked", "n_fail", "pass_rate", "status"},
    "dq_completeness": {"evidence_column", "n_rows", "n_missing", "pct_missing"},
    "dq_prevalence": {"method", "level", "group_name", "n", "periodontitis", "periodontitis_ci_low",
                      "periodontitis_ci_high", "stage3_4"},
    "dq_temporal": {"method", "n_later_visits", "perio_resolved", "stage_drop", "pairs", "better", "same", "worse"},
    "dq_transitions": {"method", "from_status", "to_status", "n", "row_pct", "direction"},
    "dq_concordance": {"method_a", "method_b", "n", "pct_agree", "kappa"},
    "dq_visits": {"visit_id", "person_id", "clinic", "visit_date", "visit_seq", "truth_status", "notes",
                  "exam_form", "proc_dx_completed", "proc_dx_planned", "probing_chart", "algorithm_v0",
                  "algorithm_design"},
    "dq_injected_errors": {"injected_errors", "caught_share", "flag_rate_without_error"},
}
PROVENANCE = {"sha256", "source_files"}


@pytest.fixture(scope="module")
def dq():
    return gt.dq_tables(DATASETS_DIR)


def test_every_dq_table_has_its_columns_and_provenance(dq):
    assert set(dq) == set(DQ)
    for name, cols in DQ.items():
        df = dq[name]
        assert len(df), name
        assert cols | PROVENANCE <= set(df.columns), (name, (cols | PROVENANCE) - set(df.columns))
        assert df.sha256.str.fullmatch(r"[0-9a-f]{64}").all(), name


def test_no_note_text_reaches_a_dq_table(dq):
    # the evidence columns are statuses, never the note itself
    statuses = {"unknown", "healthy_gingivitis", "healthy", "gingivitis"} | {f"periodontitis_stage_{i}" for i in range(1, 5)}
    for col in ("notes", "exam_form", "probing_chart", "algorithm_design", "truth_status"):
        assert set(dq["dq_visits"][col].dropna()) <= statuses, col
    assert "text" not in " ".join(c for df in dq.values() for c in df.columns)


def test_checks_hold_the_overall_rows_and_every_clinic(dq):
    c = dq["dq_checks"]
    overall = c[c.clinic == "All"]
    assert len(overall) == 16 and c.clinic.nunique() == 1 + 8


def test_transitions_are_long_form_with_row_shares_and_direction(dq):
    t = dq["dq_transitions"]
    assert len(t) == 25
    sums = t.groupby("from_status").row_pct.sum()
    assert ((sums - 100).abs() < 1e-6).all()
    worse = t[(t.from_status == "healthy_gingivitis") & (t.to_status == "periodontitis_stage_1")]
    better = t[(t.from_status == "periodontitis_stage_2") & (t.to_status == "periodontitis_stage_1")]
    assert worse.direction.item() == "worse" and better.direction.item() == "better"


def test_prevalence_holds_clinics_and_scales(dq):
    p = dq["dq_prevalence"]
    assert set(p.level) == {"clinic", "scale"}
    assert p[p.level == "clinic"].group_name.nunique() == 8


def test_dq_tables_are_the_same_on_every_build():
    a, b = gt.dq_tables(DATASETS_DIR), gt.dq_tables(DATASETS_DIR)
    for name in a:
        assert a[name].equals(b[name]), name


def test_load_results_overwrites_every_grader_table():
    # spec 019 US1: the job writes each table whole, so a rerun leaves the same rows
    from dental_omop_nlp.paths import REPO_ROOT
    nb = (REPO_ROOT / "databricks" / "notebooks" / "10_load_results.py").read_text()
    assert "grader_tables.dq_tables(data_dir)" in nb
    assert '.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(table(name))' in nb
