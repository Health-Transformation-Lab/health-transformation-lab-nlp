"""Spec 006: the three site storage designs give identical derived measures on Postgres."""

import os
import random
import uuid

import pandas as pd
import pytest

from health_transformation_lab_nlp.site_designs import DESIGNS, derived_sql, sql_stats

URL = os.environ.get("DENTAL_TEST_DB_URL")


def test_sql_stats_rank_designs():
    a, b, c = (sql_stats(d) for d in DESIGNS)
    assert a["joins"] > b["joins"] > c["joins"] == 0
    assert b["decode_calls"] > 0 and a["decode_calls"] >= 1 and c["decode_calls"] == 0
    assert "{schema}" not in derived_sql("c_site_columns", "x")


@pytest.mark.skipif(not URL, reason="set DENTAL_TEST_DB_URL to a Postgres database")
def test_three_designs_match_python():
    from sqlalchemy import create_engine, text

    from health_transformation_lab_nlp.labels import PerioChart
    from health_transformation_lab_nlp.site_designs import load_design, run_derived, write_back_derived
    from health_transformation_lab_nlp.sites import cdc_aap, derive, draw_mouth
    from health_transformation_lab_nlp.synthetic import draw_chart

    sp, tp, vis, ref = [], [], [], []
    for vid in range(1, 41):
        rng = random.Random(vid)
        c = draw_chart(60, rng)
        c = PerioChart(c.max_probing_depth_mm, c.bop_pct, c.max_cal_mm, c.rbl_pct, c.teeth_lost_perio)
        s, t = draw_mouth(c, 0 if c.max_cal_mm < 1 else 40, rng)
        pid = (vid + 1) // 2                                   # two visits per person: sites shared over time
        sp.append(s.assign(visit_id=vid, person_id=pid))
        tp.append(t.assign(visit_id=vid, person_id=pid))
        vis.append({"visit_id": vid, "person_id": pid, "visit_date": f"2021-{(vid % 12) + 1:02d}-01"})
        d = derive(s, t)
        ref.append({"visit_id": vid, **d, "cdc_aap_2012": cdc_aap(d)})
    sites, teeth, visits, ref = pd.concat(sp), pd.concat(tp), pd.DataFrame(vis), pd.DataFrame(ref)
    eng = create_engine(URL)
    tag = uuid.uuid4().hex[:6]
    try:
        for design in DESIGNS:
            schema = f"site_{design[0]}_{tag}"
            n = load_design(eng, design, schema, sites, teeth, visits)
            assert n["measurement_rows"] == 3 * len(sites) + 3 * len(teeth)
            got, _ = run_derived(eng, design, schema, repeats=1)
            m = ref.merge(got, on="visit_id", suffixes=("", "_db"))
            assert len(m) == len(ref), design
            for col in [c for c in ref.columns if c not in ("visit_id", "cdc_aap_2012")]:
                assert (m[col].astype(float) - m[f"{col}_db"].astype(float)).abs().max() < 1e-9, (design, col)
            assert (m["cdc_aap_2012"] == m["cdc_aap_2012_db"]).all(), design
            if design == "c_site_columns":
                k = write_back_derived(eng, schema, got.drop(columns="cdc_aap_2012"), visits, 10_000_000)
                assert k == 14 * len(got)
    finally:
        with eng.begin() as c:
            for design in DESIGNS:
                c.execute(text(f"DROP SCHEMA IF EXISTS site_{design[0]}_{tag} CASCADE"))
