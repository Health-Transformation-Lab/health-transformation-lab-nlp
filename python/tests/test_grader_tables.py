"""Spec 018: the tables the two graders read, built from the committed CSVs (US1 data quality, US3 lab grader)."""

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
    # spec 018 US1: the job writes each table whole, so a rerun leaves the same rows
    from dental_omop_nlp.paths import REPO_ROOT
    nb = (REPO_ROOT / "databricks" / "notebooks" / "10_load_results.py").read_text()
    assert "grader_tables.dq_tables(data_dir)" in nb and "grader_tables.lab_tables(data_dir)" in nb
    assert '.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(table(name))' in nb


# ---------------------------------------------------------------- the lab grader (US3)

LAB = {
    "grader_questions": {"question_id", "category", "category_order", "level", "n_key_points", "source", "simulated"},
    "grader_answers": {"question_id", "model", "with_agent", "key_points_covered", "score", "harm", "cost_usd",
                       "judge", "run_id", "simulated"},
}


@pytest.fixture(scope="module")
def sim():
    return gt.simulate_grader(seed=2026)


def test_simulated_sample_is_seeded_and_reproducible(sim):
    again = gt.simulate_grader(seed=2026)
    for name in sim:
        assert sim[name].equals(again[name]), name
    assert not sim["grader_answers"].equals(gt.simulate_grader(seed=7)["grader_answers"])


def test_simulated_sample_has_the_spec_shape(sim):
    q, a = sim["grader_questions"], sim["grader_answers"]
    assert set(sim) == set(LAB)
    for name, cols in LAB.items():
        assert cols <= set(sim[name].columns), (name, cols - set(sim[name].columns))
    assert q.simulated.all() and a.simulated.all()                          # never a result
    assert a.model.str.startswith("sim:").all() and a.judge.str.startswith("sim:").all()
    assert q.groupby("category").size().eq(25).all()                         # the pitch's pilot size
    assert q.sort_values("category_order").category.iloc[0] == "Access to care"   # the mission first
    assert set(q.level) == {"L1", "L2", "L3"} and set(a.harm) <= {"S0", "S1", "S2"}
    assert (a.score == a.key_points_covered / a.question_id.map(q.set_index("question_id").n_key_points)).all()
    per_question = a.groupby(["question_id", "model"]).with_agent.nunique()
    assert per_question.eq(2).all()                                          # each model with and without the agent
    assert not set(a.judge.str.split(":").str[1]) & set(a.model.str.split(":").str[1])   # never self-judged


def test_lab_tables_use_real_files_when_present_else_the_sample(tmp_path, sim):
    out = gt.lab_tables(tmp_path)                                            # nothing there: the seeded sample
    assert out["grader_answers"].simulated.all() and (out["grader_answers"].sha256.str.len() == 64).all()
    (tmp_path / "grader").mkdir()
    for name, df in sim.items():
        df.assign(simulated=False).to_csv(tmp_path / "grader" / f"{name}.csv", index=False)
    real = gt.lab_tables(tmp_path)
    assert not real["grader_answers"].simulated.any()
    assert real["grader_answers"].source_files.iloc[0] == "grader/grader_answers.csv"
