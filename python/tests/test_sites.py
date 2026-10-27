"""Spec 006: site-level charts, derived measures, 2017 AAP/EFP and 2012 CDC/AAP from sites."""

import random

import pandas as pd
import pytest

from dental_omop_nlp.labels import PerioChart, label_chart
from dental_omop_nlp.sites import (
    INTERPROXIMAL,
    SITES,
    aap_from_derived,
    cdc_aap,
    derive,
    derive_all,
    draw_mouth,
)
from dental_omop_nlp.synthetic import draw_chart


def _mouths(n=300):
    for s in range(n):
        rng = random.Random(s)
        c = draw_chart(rng.randint(25, 80), rng)
        pct = 0 if c.max_cal_mm < 1 else rng.choice([10, 25, 45, 80])
        yield c, pct, draw_mouth(c, pct, rng)


def test_mouth_shape():
    _, _, (sites, teeth) = next(_mouths(1))
    assert len(teeth) == 32 and set(SITES) == {"MB", "B", "DB", "ML", "L", "DL"}
    present = teeth[teeth.present].tooth
    assert set(sites.tooth) == set(present) and len(sites) == 6 * len(present)
    assert INTERPROXIMAL == {"MB", "DB", "ML", "DL"}


def test_sites_reproduce_the_visit_chart():
    for c, _, (sites, teeth) in _mouths():
        d = derive(sites, teeth)
        assert abs(d["max_cal_mm"] - c.max_cal_mm) < 1e-9
        assert abs(d["max_probing_depth_mm"] - c.max_probing_depth_mm) < 1e-9
        assert d["teeth_lost_perio"] == c.teeth_lost_perio
        assert (d["bop_pct"] >= 10) == (c.bop_pct >= 10)


def test_stage_from_sites_equals_stage_from_chart():
    for c, _, (sites, teeth) in _mouths():
        d = derive(sites, teeth)
        assert aap_from_derived(d, rbl_pct=c.rbl_pct) == label_chart(c).value


def _one_mouth(cal, pd_):
    """cal/pd: {(tooth, site): mm}; other sites 0 / 2 mm; all 32 teeth present."""
    rows = [{"tooth": t, "site": s, "pd_mm": pd_.get((t, s), 2.0), "cal_mm": cal.get((t, s), 0.0), "bop": False}
            for t in range(1, 33) for s in SITES]
    teeth = pd.DataFrame({"tooth": range(1, 33), "present": True, "missing_reason": "",
                          "furcation_class": 0, "mobility_degree": 0})
    return derive(pd.DataFrame(rows), teeth)


@pytest.mark.parametrize("cal,pdd,want", [
    ({(3, "MB"): 6, (14, "DL"): 6}, {(3, "MB"): 5}, "severe"),
    ({(3, "MB"): 6, (3, "DB"): 6}, {(3, "MB"): 5}, "mild"),           # CAL 6 on one tooth only: not severe/moderate
    ({(3, "MB"): 4, (14, "DL"): 4}, {}, "moderate"),
    ({}, {(3, "MB"): 5, (14, "DL"): 5}, "moderate"),
    ({(3, "MB"): 3, (14, "DL"): 3}, {(3, "MB"): 4, (14, "DL"): 4}, "mild"),
    ({}, {(3, "MB"): 5}, "mild"),                                      # one site PD >= 5
    ({(3, "MB"): 3, (14, "DL"): 3}, {(3, "MB"): 4}, "none"),           # only one tooth with PD >= 4
    ({(3, "B"): 7, (14, "L"): 7}, {(3, "B"): 6}, "none"),              # buccal/lingual sites don't count
])
def test_cdc_aap(cal, pdd, want):
    assert cdc_aap(_one_mouth(cal, pdd)) == want


def test_derived_counts_distinct_teeth():
    d = _one_mouth({(3, "MB"): 6, (3, "DB"): 6, (14, "ML"): 4}, {})
    assert d["n_teeth_ip_cal6"] == 1 and d["n_teeth_ip_cal4"] == 2 and d["n_teeth_ip_cal3"] == 2


def test_many_teeth_lost():
    rng = random.Random(1)
    c = PerioChart(8, 60, 9, 70, 10)
    sites, teeth = draw_mouth(c, 80, rng)
    assert derive(sites, teeth)["teeth_lost_perio"] == 10


def test_draw_mouth_output_is_unchanged_for_seeded_charts():
    """Speed-ups must keep every random draw in order: parity and committed data depend on it."""
    import hashlib
    parts = []
    for i, (_, _, (sites, teeth)) in enumerate(_mouths(60)):
        parts += [sites.assign(v=i).to_csv(index=False), teeth.assign(v=i).to_csv(index=False)]
    assert hashlib.sha256("".join(parts).encode()).hexdigest() == \
        "0b9ae13bf6fafe4f674c7ef4ab0d146420a42f7a198b0bfd57513f4899535943"


def test_derive_all_equals_derive_per_visit():
    """derive_all does every visit in one pass; it must match derive() exactly."""
    site_parts, tooth_parts, want = [], [], []
    for i, (_, _, (sites, teeth)) in enumerate(_mouths(300)):
        site_parts.append(sites.assign(visit_id=i))
        tooth_parts.append(teeth.assign(visit_id=i))
        want.append({"visit_id": i, **derive(sites, teeth)})
    got = derive_all(pd.concat(site_parts, ignore_index=True), pd.concat(tooth_parts, ignore_index=True))
    pd.testing.assert_frame_equal(got.reset_index(), pd.DataFrame(want), check_exact=True)
