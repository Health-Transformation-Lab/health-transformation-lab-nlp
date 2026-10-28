"""Spec 026 US1: a KEEPER-style case profile for every synthetic visit, structured values only."""

import pandas as pd
import pytest

from health_transformation_lab_nlp import case_profile as cp
from health_transformation_lab_nlp import plausibility
from health_transformation_lab_nlp.paths import DATASETS_DIR

CATEGORIES = ["Demographics", "Presentation", "Visit context", "Measurements", "Tests and imaging", "Risk factors",
              "Treatment", "Other readings", "After the visit"]


def _visit(**kw):
    base = {"visit_id": 1, "person_id": 10, "clinic_id": 3, "visit_seq": 0, "visit_date": "2021-01-01", "age": 50,
            "charted": True, "treated_before": False, "cigarettes_per_day": 0, "diabetes": False, "hba1c":
            float("nan"), "rec_max_probing_depth_mm": 5.0, "rec_bop_pct": 35.0, "rec_max_cal_mm": 4.0,
            "rec_rbl_pct": 20.0, "rec_teeth_lost_perio": 0.0, "rec_pct_teeth_involved": 40.0, "notes":
            "periodontitis_stage_2", "exam_form": "periodontitis_stage_2", "proc_codes_completed":
            "periodontitis_stage_2", "proc_codes_planned": "unknown", "proc_dx_completed": "periodontitis_stage_2",
            "proc_dx_planned": "unknown", "probing_chart": "periodontitis_stage_2", "radiograph_ai": "unknown",
            "algorithm_v0": "periodontitis_stage_2", "algorithm_design": "periodontitis_stage_2", "in_review":
            False}
    return base | kw


def _value(profile, visit_id, item):
    row = profile[(profile.visit_id == visit_id) & (profile["item"] == item)]
    assert len(row) == 1, (visit_id, item)
    return row["value"].item()


@pytest.fixture
def two_visits():
    first = _visit()
    later = _visit(visit_id=2, visit_seq=1, visit_date="2021-07-01", proc_dx_completed="periodontitis_stage_1",
                   rec_max_cal_mm=1.0)
    return pd.DataFrame([first, later])


def test_every_visit_gets_the_nine_categories_in_order(two_visits):
    p = cp.build_profiles(two_visits)
    for vid in (1, 2):
        cats = p[p.visit_id == vid].sort_values(["category_order", "item_order"]).category.drop_duplicates()
        assert list(cats) == CATEGORIES


def test_values_are_shown_with_their_units(two_visits):
    p = cp.build_profiles(two_visits)
    assert _value(p, 1, "max attachment loss (CAL)") == "4"
    assert p[(p.visit_id == 1) & (p["item"] == "max attachment loss (CAL)")]["unit"].item() == "mm"
    assert _value(p, 1, "recorded diagnosis code, completed") == "periodontitis_stage_2"
    assert _value(p, 1, "diabetes") == "no"


def test_missing_values_and_unknown_statuses_read_not_recorded():
    v = _visit(charted=False, rec_max_probing_depth_mm=float("nan"), rec_bop_pct=float("nan"),
               rec_max_cal_mm=float("nan"), rec_rbl_pct=float("nan"), rec_teeth_lost_perio=float("nan"),
               rec_pct_teeth_involved=float("nan"), probing_chart="unknown", proc_dx_planned="unknown")
    p = cp.build_profiles(pd.DataFrame([v]))
    assert set(p[p.category == "Measurements"]["value"]) == {cp.NOT_RECORDED}
    assert _value(p, 1, "HbA1c") == cp.NOT_RECORDED
    assert _value(p, 1, "recorded diagnosis code, planned") == cp.NOT_RECORDED
    assert _value(p, 1, "probing chart reading") == cp.NOT_TAKEN


def test_the_last_visit_has_no_later_visit_and_the_earlier_one_shows_what_came_next(two_visits):
    p = cp.build_profiles(two_visits)
    assert _value(p, 2, "next visit's recorded code") == cp.NO_LATER_VISIT
    assert _value(p, 1, "next visit's recorded code") == "periodontitis_stage_1"
    # the later visit's code dropped a stage: the plausibility checks say so, at the next visit
    flags = _value(p, 1, "next visit's plausibility flags")
    expected = plausibility.check_history(cp.history_frame(two_visits), "proc_dx_completed")
    assert flags == ", ".join(f for f in plausibility.FLAGS if expected.loc[expected.visit_id == 2, f].item())
    assert "stage_drop" in flags and "cal_drop" in flags
    assert _value(p, 2, "next visit's plausibility flags") == cp.NO_LATER_VISIT


def test_a_visit_with_a_clean_next_visit_says_none(two_visits):
    v = two_visits.assign(proc_dx_completed="periodontitis_stage_2", rec_max_cal_mm=4.0)
    assert _value(cp.build_profiles(v), 1, "next visit's plausibility flags") == "none"


def test_only_statuses_and_measures_are_read_never_note_text(two_visits):
    p = cp.build_profiles(two_visits)
    # `notes` in visits_structured is the note reader's status, not the note: the profile shows it as a status
    assert _value(p, 1, "note reader") == "periodontitis_stage_2"
    assert p["value"].str.len().max() <= 60
    assert "text" not in " ".join(p.columns)


def test_profile_items_name_their_source_columns():
    cols = {c for _, _, c, _ in cp.PROFILE_ITEMS if c}
    assert cols <= set(_visit())
    assert [c for c in dict.fromkeys(cat for cat, *_ in cp.PROFILE_ITEMS)] == CATEGORIES


def test_the_built_study_has_one_complete_profile_per_visit():
    v = pd.read_csv(DATASETS_DIR / "visits_structured.csv")
    p = cp.build_profiles(v)
    assert p.visit_id.nunique() == len(v)
    per_visit = p.groupby("visit_id").category.nunique()
    assert (per_visit == len(CATEGORIES)).all()
    assert len(p) == len(v) * len(cp.PROFILE_ITEMS)
    assert p["value"].notna().all()
