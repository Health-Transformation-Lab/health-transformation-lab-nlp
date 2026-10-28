"""Spec 013 G7: completeness after Zozus et al. (element, column value, row value) on three scales."""

import pandas as pd
import pytest

from health_transformation_lab_nlp.completeness import (
    CHART_INPUTS,
    column_completeness,
    complete_cases,
    element_completeness,
    prevalence_by_scale,
    row_completeness,
)


def _v():
    return pd.DataFrame({
        "visit_id": [1, 2, 3, 4],
        "person_id": [1, 2, 3, 4],
        "visit_date": ["2021-01-01"] * 4,
        "notes": ["healthy", "unknown", "periodontitis_stage_2", "periodontitis_stage_3"],
        "exam_form": ["healthy", "gingivitis", "unknown", "periodontitis_stage_3"],
        "proc_codes_planned": ["healthy", "healthy", "periodontitis_stage_2", "periodontitis_stage_2"],
        "charted": [True, True, False, True],
        "rec_max_cal_mm": [0.0, 1.0, None, 5.0],
        "rec_bop_pct": [5.0, None, None, 40.0],
        "rec_max_probing_depth_mm": [2.0, 3.0, None, 6.0],
        "rec_teeth_lost_perio": [0, 0, None, 1],
        "in_review": [False, False, True, True],
        "algorithm_design": ["healthy", "gingivitis", "periodontitis_stage_2", "periodontitis_stage_3"],
    })


def test_element_completeness_lists_missing_tables_and_columns():
    expected = {"perioexam": ["PerioExamNum", "ExamDate"], "periomeasure": ["ToothValue"]}
    actual = {"perioexam": ["PerioExamNum"]}
    e = element_completeness(expected, actual)
    assert e.set_index(["table", "column"])["present"].to_dict() == {
        ("perioexam", "PerioExamNum"): True, ("perioexam", "ExamDate"): False,
        ("periomeasure", "ToothValue"): False}


def test_column_completeness_counts_unknown_and_null_as_missing():
    c = column_completeness(_v(), ["notes", "rec_bop_pct"]).set_index("column")
    assert c.loc["notes", "pct_missing"] == 25.0
    assert c.loc["rec_bop_pct", "pct_missing"] == 50.0


def test_row_completeness_needs_every_chart_input_on_charted_visits():
    r = row_completeness(_v(), CHART_INPUTS)
    assert (r["n_rows"], r["n_complete"]) == (3, 2) and r["pct_complete"] == pytest.approx(200 / 3)


def test_complete_cases_need_exam_form_plan_chart_and_note():
    assert list(complete_cases(_v()).visit_id) == [1, 4]


def test_prevalence_on_three_scales():
    p = prevalence_by_scale(_v(), "algorithm_design").set_index("scale")
    assert list(p.index) == ["all_visits", "complete_cases", "reference_set"]
    assert p.loc["all_visits", "n_known"] == 4 and p.loc["all_visits", "periodontitis"] == 0.5
    assert p.loc["complete_cases", "periodontitis"] == 0.5
    assert p.loc["reference_set", "periodontitis"] == 1.0
