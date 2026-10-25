"""Spec 005 US2: synthetic patient histories and temporal plausibility checks."""

import random

import pandas as pd

from dental_omop_nlp.labels import LABELS, label_chart
from dental_omop_nlp.plausibility import FLAGS, check_history
from dental_omop_nlp.synthetic import RiskFactors, draw_history


def _hist(seed, n=6, age=50, risk=RiskFactors(0, None)):
    return draw_history(age, n, risk, random.Random(seed))


def test_attachment_bone_and_teeth_never_recover():
    for s in range(300):
        h = _hist(s)
        for a, b in zip(h, h[1:]):
            assert b.chart.max_cal_mm >= a.chart.max_cal_mm
            assert b.chart.rbl_pct >= a.chart.rbl_pct
            assert b.chart.teeth_lost_perio >= a.chart.teeth_lost_perio


def test_periodontitis_patient_stays_periodontitis_and_stage_never_drops():
    for s in range(300):
        st = [v.status for v in _hist(s)]
        for a, b in zip(st, st[1:]):
            if a.is_periodontitis:
                assert b.is_periodontitis
                assert int(b.value[-1]) >= int(a.value[-1])


def test_stage_kept_after_treatment_even_if_pockets_shrink():
    for s in range(300):
        h = _hist(s)
        for v in h:   # the stage reached is kept; the current chart alone may read lower after treatment
            assert LABELS.index(v.status.value) >= LABELS.index(label_chart(v.chart).value)


def test_risk_speeds_progression():
    def mean_gain(risk):
        g = []
        for s in range(400):
            h = _hist(s, risk=risk)
            if h[0].chart.max_cal_mm >= 1:
                g.append(h[-1].chart.max_cal_mm - h[0].chart.max_cal_mm)
        return sum(g) / len(g)
    assert mean_gain(RiskFactors(20, 8.5)) > mean_gain(RiskFactors(0, None)) + 0.3


def test_treatment_lowers_pockets_and_bleeding():
    seen = 0
    for s in range(400):
        h = _hist(s)
        for a, b in zip(h, h[1:]):
            if b.treated_before and not a.treated_before:
                assert b.chart.max_probing_depth_mm <= a.chart.max_probing_depth_mm
                seen += 1
    assert seen > 20


def _visits(rows):
    cols = ["person_id", "visit_date", "charted", "max_cal_mm", "rbl_pct", "teeth_lost_perio", "status"]
    return pd.DataFrame(rows, columns=cols).assign(visit_id=lambda d: range(1, len(d) + 1))


def test_flags():
    v = _visits([
        (1, "2021-01-01", True, 4, 20, 0, "periodontitis_stage_2"),
        (1, "2021-07-01", True, 2, 12, 0, "gingivitis"),      # CAL -2, RBL -8, perio -> none, stage drop
        (2, "2021-01-01", True, 5, 35, 3, "periodontitis_stage_3"),
        (2, "2021-07-01", True, 5, 35, 1, "periodontitis_stage_3"),  # teeth lost decreased
        (3, "2021-01-01", True, 2, 10, 0, "periodontitis_stage_1"),
        (3, "2021-07-01", False, None, None, 0, "unknown"),           # not charted: skipped
        (3, "2022-01-01", True, 2.2, 11, 0, "periodontitis_stage_1"),  # fine
    ])
    f = check_history(v).set_index("visit_id")
    assert set(FLAGS) <= set(f.columns)
    assert f.loc[2, ["cal_drop", "rbl_drop", "perio_resolved", "stage_drop"]].all()
    assert f.loc[4, "teeth_regained"] and not f.loc[4, "cal_drop"]
    assert not f.loc[7, FLAGS].any() and not f.loc[1, FLAGS].any()
    assert f["any_flag"].sum() == 2
