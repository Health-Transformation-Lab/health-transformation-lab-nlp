"""OMOP CDM 5.4 + dental extension on Postgres (Lakebase is Postgres).

Runs when DENTAL_TEST_DB_URL points at a Postgres database it may write to,
e.g. postgresql://postgres@localhost:5432/postgres (CI uses a postgres:16
service). Skipped otherwise.
"""

import os
import uuid

import pandas as pd
import pytest

from health_transformation_lab_nlp.db import conform, load_omop, perio_chart_from_db
from health_transformation_lab_nlp.labels import label_row
from health_transformation_lab_nlp.paths import LABELS_DIR, REPO_ROOT

URL = os.environ.get("DENTAL_TEST_DB_URL")


def test_conform_adds_required_cdm_columns():
    t = conform({"person": pd.DataFrame({"person_id": [1], "gender_concept_id": [8532], "year_of_birth": [1970]}),
                 "visit_occurrence": pd.DataFrame({"visit_occurrence_id": [1], "person_id": [1],
                                                   "visit_concept_id": [9202],
                                                   "visit_start_date": [pd.Timestamp("2021-01-01").date()]})})
    assert {"race_concept_id", "ethnicity_concept_id"} <= set(t["person"].columns)
    v = t["visit_occurrence"]
    assert v.loc[0, "visit_end_date"] == v.loc[0, "visit_start_date"] and v.loc[0, "visit_type_concept_id"] == 32817


@pytest.mark.skipif(not URL, reason="set DENTAL_TEST_DB_URL to a Postgres database")
def test_perio_chart_view_on_postgres_matches_labels():
    schema = f"cdm_test_{uuid.uuid4().hex[:8]}"
    omop_dir = REPO_ROOT / "data" / "omop"
    if not (omop_dir / "measurement.parquet").exists():
        pytest.skip("run scripts/01_build_dataset.py first")
    from sqlalchemy import create_engine, text
    eng = create_engine(URL)
    try:
        n = load_omop(eng, omop_dir, schema)
        assert n["measurement"] > 0 and n["concept"] >= 11
        view = perio_chart_from_db(eng, schema)
        notes = pd.read_parquet(LABELS_DIR / "labeled_notes.parquet")
        m = notes.merge(view, left_on="note_id", right_on="visit_occurrence_id", suffixes=("", "_db"))
        assert len(m) == len(notes)
        for c in ("max_probing_depth_mm", "bop_pct", "max_cal_mm", "rbl_pct", "teeth_lost_perio"):
            assert (m[c] - m[f"{c}_db"]).abs().max() < 1e-9, c
        assert (m.apply(lambda r: label_row({k.removesuffix("_db"): r[k] for k in r.index if k.endswith("_db")}),
                        axis=1) == m["label"]).all()
    finally:
        with eng.begin() as c:
            c.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
