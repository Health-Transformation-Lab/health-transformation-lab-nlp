"""AAP staging and grading worksheet (docs/staging_grading.md):
https://www.perio.org/wp-content/uploads/2019/08/Staging-and-Grading-Periodontitis.pdf
"""

import pytest

from health_transformation_lab_nlp.labels import PerioChart, Status, extent_of, grade_of, label_chart

P1, P2, P3, P4 = Status.P1, Status.P2, Status.P3, Status.P4


def chart(cal=None, rbl=None, pd=3.0, bop=30.0, lost=0, **kw):
    return PerioChart(pd, bop, cal, rbl, lost, **kw)


# ---- initial stage: CAL first, RBL only if CAL not available
@pytest.mark.parametrize("cal,rbl,want", [
    (2, 25, P1),        # CAL decides even when RBL reads higher
    (4, 10, P2),
    (5, 20, P3),
    (None, 10, P1),     # no CAL charted: use RBL
    (None, 25, P2),
    (None, 40, P3),
])
def test_initial_stage_cal_then_rbl(cal, rbl, want):
    assert label_chart(chart(cal, rbl)) == want


def test_no_interdental_cal_is_not_periodontitis():
    assert label_chart(chart(0.5, 20, bop=30)) == Status.GINGIVITIS
    assert label_chart(chart(0, 0, bop=5)) == Status.HEALTHY
    assert label_chart(chart(None, 0, bop=5)) == Status.HEALTHY


def test_needs_cal_or_rbl():
    with pytest.raises(ValueError):
        chart(None, None)


# ---- tooth loss due to periodontitis
@pytest.mark.parametrize("cal,lost,want", [(2, 1, P3), (3, 4, P3), (6, 4, P3), (3, 5, P4), (6, 5, P4)])
def test_tooth_loss(cal, lost, want):
    assert label_chart(chart(cal, 10, lost=lost)) == want


# ---- complexity shifts the stage up
@pytest.mark.parametrize("kw,want", [
    ({"pd": 4.0}, P1),                     # stage I: max PD <= 4
    ({"pd": 5.0}, P2),                     # deeper than stage I allows
    ({"pd": 6.0}, P3),                     # PD >= 6
    ({"vertical_defect_mm": 3}, P3),       # vertical bone loss >= 3 mm
    ({"furcation_class": 2}, P3),          # class II or III furcation
    ({"furcation_class": 1}, P1),
    ({"pd": 6.0, "mobility_degree": 2}, P4),   # secondary occlusal trauma
    ({"pd": 6.0, "remaining_teeth": 19}, P4),  # < 20 teeth (10 opposing pairs)
    ({"pd": 6.0, "complex_rehab": True}, P4),  # masticatory dysfunction, bite collapse, drifting, severe ridge defect
])
def test_complexity_shifts(kw, want):
    assert label_chart(chart(2, 10, **kw)) == want


def test_stage_iv_complexity_needs_stage_iii_first():
    assert label_chart(chart(2, 10, mobility_degree=2)) == P1
    assert label_chart(chart(6, 40, mobility_degree=2)) == P4


def test_complexity_never_lowers_stage():
    assert label_chart(chart(6, 40, pd=4.0)) == P3


def test_complexity_ignored_without_attachment_loss():
    assert label_chart(chart(0, 0, pd=6.0, bop=40)) == Status.GINGIVITIS


# ---- grade: start at B; direct evidence first; then %RBL/age; then modifiers
def test_grade_defaults_to_b_without_evidence():
    assert grade_of(P2, None, 45) == "B"


@pytest.mark.parametrize("loss,want", [(0, "A"), (1.5, "B"), (2.0, "C")])
def test_grade_direct_evidence_wins(loss, want):
    assert grade_of(P2, 60, 30, loss_5yr_mm=loss) == want   # ratio 2.0 would say C


@pytest.mark.parametrize("rbl,age,want", [(10, 50, "A"), (20, 40, "B"), (50, 50, "B"), (60, 40, "C")])
def test_grade_indirect_ratio(rbl, age, want):
    assert grade_of(P2, rbl, age) == want


@pytest.mark.parametrize("kw,want", [
    ({"cigarettes_per_day": 5}, "B"), ({"cigarettes_per_day": 10}, "C"),
    ({"hba1c": 6.5}, "B"), ({"hba1c": 7.0}, "C"),
    ({"hba1c": 5.4, "diabetes": False}, "A"),       # normoglycemic: no modifier
])
def test_grade_modifiers(kw, want):
    assert grade_of(P2, 10, 50, **kw) == want


def test_grade_na_without_periodontitis():
    assert grade_of(Status.GINGIVITIS, 0, 40) == "NA"


# ---- extent
def test_extent():
    assert extent_of(P2, 29.9) == "localized"
    assert extent_of(P2, 30) == "generalized"
    assert extent_of(P3, 10, molar_incisor=True) == "molar_incisor"
    assert extent_of(Status.HEALTHY, 50) == "NA"
