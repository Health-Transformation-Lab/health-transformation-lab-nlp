"""Spec 013 G8: phenotype transitions from a visit to one 1-2 years later, untreated people only."""

import pandas as pd

from health_transformation_lab_nlp.plausibility import transition_pairs, transition_summary


def _visits(rows):
    return pd.DataFrame(rows, columns=["visit_id", "person_id", "visit_date", "treated_before", "status"])


def test_pairs_take_the_first_visit_one_to_two_years_later():
    v = _visits([
        (1, 1, "2020-01-01", False, "periodontitis_stage_2"),
        (2, 1, "2020-06-01", False, "periodontitis_stage_2"),   # too soon after visit 1
        (3, 1, "2021-03-01", False, "periodontitis_stage_3"),   # 425 days after visit 1
        (4, 1, "2021-09-01", False, "healthy"),
    ])
    p = transition_pairs(v, "status")
    first = p[p.visit_id == 1].iloc[0]
    assert first.next_visit_id == 3 and first.change == "worse"
    assert first.from_status == "periodontitis_stage_2" and first.to_status == "periodontitis_stage_3"
    # visit 2 -> visit 4 is 457 days: an improvement from stage II to healthy/gingivitis
    assert p[p.visit_id == 2].iloc[0].change == "better"


def test_treatment_in_between_drops_the_pair():
    v = _visits([
        (1, 1, "2020-01-01", False, "periodontitis_stage_3"),
        (2, 1, "2021-02-01", True, "periodontitis_stage_1"),    # treated between the two visits
        (3, 2, "2020-01-01", True, "periodontitis_stage_3"),
        (4, 2, "2021-02-01", True, "periodontitis_stage_3"),    # treated before both: kept
    ])
    p = transition_pairs(v, "status")
    assert list(p.person_id) == [2]


def test_unknown_and_out_of_window_visits_are_skipped():
    v = _visits([
        (1, 1, "2020-01-01", False, "unknown"),
        (2, 1, "2021-01-15", False, "healthy"),
        (3, 1, "2023-06-01", False, "gingivitis"),               # > 2 years after visit 2
    ])
    assert transition_pairs(v, "status").empty


def test_summary_uses_five_categories_and_counts_changes():
    v = _visits([
        (1, 1, "2020-01-01", False, "healthy"),
        (2, 1, "2021-01-15", False, "gingivitis"),               # same five-category status
        (3, 2, "2020-01-01", False, "periodontitis_stage_2"),
        (4, 2, "2021-01-15", False, "periodontitis_stage_1"),
    ])
    matrix, shares = transition_summary(transition_pairs(v, "status"))
    assert matrix.loc["healthy_gingivitis", "healthy_gingivitis"] == 1
    assert matrix.loc["periodontitis_stage_2", "periodontitis_stage_1"] == 1
    assert shares == {"pairs": 2, "better": 0.5, "same": 0.5, "worse": 0.0}
