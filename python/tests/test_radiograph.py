"""Spec 003: structured radiograph findings."""

import random

import pandas as pd

from dental_omop_nlp.labels import PerioChart
from dental_omop_nlp.radiograph import FEATURES, features, read_radiograph, simulate_radiograph, summary


def _rad(chart, pct=50, seed=1, **kw):
    return simulate_radiograph(chart, pct_teeth_involved=pct, rng=random.Random(seed), **kw)


def test_reader_stage_rules():
    # < 15% is within measurement noise: no call
    assert read_radiograph({"present": True, "quality": "ok", "max_rbl_pct": 12, "teeth": [1]}) == "unknown"
    # one noisy tooth isn't enough
    assert read_radiograph({"present": True, "quality": "ok", "max_rbl_pct": 30, "n_teeth_rbl15": 1, "teeth": [1]}) == "unknown"
    assert read_radiograph({"present": True, "quality": "ok", "max_rbl_pct": 25, "teeth": [1]}) == "periodontitis_stage_2"
    # 38% with many teeth missing: stage III, never IV (cause of loss not visible)
    r = {"present": True, "quality": "ok", "max_rbl_pct": 38, "teeth": [1], "missing_teeth": list(range(6))}
    assert read_radiograph(r) == "periodontitis_stage_3"


def test_reader_unknown_cases():
    assert read_radiograph({"present": True, "quality": "ok", "max_rbl_pct": 2, "teeth": [1]}) == "unknown"
    assert read_radiograph({"present": False}) == "unknown"
    assert read_radiograph({"present": True, "quality": "failed"}) == "unknown"


def test_simulator_tracks_chart():
    hits = 0
    for s in range(200):
        r = _rad(PerioChart(6, 40, 6, 40, 0), seed=s, availability=1.0, failure_rate=0.0)
        hits += 30 <= r["max_rbl_pct"] <= 50
    assert hits >= 170


def test_bitewing_is_posterior_only():
    r = _rad(PerioChart(5, 30, 4, 25), availability=1.0, failure_rate=0.0, image="4BWX")
    assert all(t["tooth"] not in range(6, 12) and t["tooth"] not in range(22, 28) for t in r["teeth"])


def test_features_and_summary_without_radiograph():
    r = _rad(PerioChart(2, 5, 0, 0), availability=0.0)
    f = features(r)
    assert set(FEATURES) <= set(f) and f["rad_present"] == 0
    assert "no radiograph" in summary(r).lower()


def test_fusion_rung_handles_missing_radiographs():
    from dental_omop_nlp.registry import load_registry
    from dental_omop_nlp.rungs import make_rung
    rng = random.Random(0)
    rows = []
    for i in range(240):
        lab = ["healthy", "gingivitis", "periodontitis_stage_2", "periodontitis_stage_3"][i % 4]
        rbl = {"healthy": 0, "gingivitis": 2, "periodontitis_stage_2": 25, "periodontitis_stage_3": 45}[lab]
        r = _rad(PerioChart(3, 20, 3 if rbl else 0, rbl), seed=i, availability=0.8)
        rows.append({"note_text": f"note {lab.split('_')[0]} visit {rng.randint(0, 9)}", "label": lab, **features(r)})
    df = pd.DataFrame(rows)
    m = make_rung("fusion_tfidf_rad", load_registry()).fit(df.iloc[:180])
    pred, proba = m.predict(df.iloc[180:])
    assert len(pred) == 60 and proba.shape == (60, 6)
