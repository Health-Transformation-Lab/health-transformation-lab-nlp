"""Spec 005 US2: synthetic patient histories and temporal plausibility checks."""

import random

import pandas as pd

from health_transformation_lab_nlp.labels import LABELS, label_chart
from health_transformation_lab_nlp.plausibility import FLAGS, check_history
from health_transformation_lab_nlp.synthetic import RiskFactors, draw_history


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


def test_check_history_single_pass_equals_the_per_person_version():
    """check_history walks the sorted visits once; it must match the per-person groupby it replaced
    (copied here), including dropping visits with no person_id."""
    import random

    import numpy as np
    import pandas as pd

    from health_transformation_lab_nlp.labels import LABELS
    from health_transformation_lab_nlp.plausibility import CAL_TOL_MM, FLAGS, RBL_TOL_PCT, check_history

    def reference(visits, status_col):
        rows = []
        for pid, g in visits.sort_values(["person_id", "visit_date", "visit_id"]).groupby("person_id", sort=False):
            last_chart, best_rank = None, None
            for r in g.itertuples():
                f = dict.fromkeys(FLAGS, False)
                if bool(r.charted) and pd.notna(r.max_cal_mm):
                    if last_chart is not None:
                        f["cal_drop"] = last_chart[0] - r.max_cal_mm > CAL_TOL_MM
                        f["rbl_drop"] = last_chart[1] - r.rbl_pct > RBL_TOL_PCT
                        f["teeth_regained"] = r.teeth_lost_perio < last_chart[2]
                    last_chart = (r.max_cal_mm, r.rbl_pct, r.teeth_lost_perio)
                s = getattr(r, status_col)
                if s in LABELS:
                    rank = LABELS.index(s)
                    if best_rank is not None and best_rank >= 2:
                        f["perio_resolved"] = rank < 2
                        f["stage_drop"] = rank < best_rank
                    best_rank = rank if best_rank is None else max(best_rank, rank)
                rows.append({"visit_id": r.visit_id, "person_id": pid, **f})
        out = pd.DataFrame(rows, columns=["visit_id", "person_id", *FLAGS])
        out["any_flag"] = out[FLAGS].any(axis=1)
        return out

    rng = random.Random(5)
    rows = []
    for v in range(400):
        rows.append({"visit_id": v, "person_id": rng.choice([*range(60), np.nan]),
                     "visit_date": f"202{rng.randint(0, 5)}-0{rng.randint(1, 9)}-01",
                     "charted": rng.random() < 0.7,
                     "max_cal_mm": rng.choice([np.nan, *[x / 2 for x in range(14)]]),
                     "rbl_pct": rng.uniform(0, 60), "teeth_lost_perio": rng.randint(0, 6),
                     "status": rng.choice([*LABELS, "unknown", None])})
    visits = pd.DataFrame(rows).sample(frac=1, random_state=1)   # unsorted, as callers may pass
    pd.testing.assert_frame_equal(check_history(visits, "status").reset_index(drop=True),
                                  reference(visits, "status").reset_index(drop=True))
