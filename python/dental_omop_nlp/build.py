"""Build the OMOP tables and the labeled note set.

Input:  Synthea CSV (patients.csv, encounters.csv) if present, otherwise a
        generated stand-in population so the pipeline runs without Java.
Output: OMOP parquet (person, visit_occurrence, measurement, note) under
        OMOP_DIR, and labeled_notes.parquet/.csv under LABELS_DIR.

Only the OMOP columns the benchmark uses are populated. The full ETL into a
complete CDM is the R side's ETL-Synthea step (r/R/01_etl_synthea.R).
"""

from __future__ import annotations

import datetime as dt
import random
from pathlib import Path

import pandas as pd

from .labels import label_chart
from .notes import render_soap_note
from .synthetic import draw_chart

LOCAL = {"PERIO_MAX_PD": 2000000001, "PERIO_BOP_PCT": 2000000002, "PERIO_MAX_CAL": 2000000003,
         "PERIO_RBL_PCT": 2000000004, "PERIO_TEETH_LOST": 2000000005}
CHART_FIELDS = {"PERIO_MAX_PD": "max_probing_depth_mm", "PERIO_BOP_PCT": "bop_pct",
                "PERIO_MAX_CAL": "max_cal_mm", "PERIO_RBL_PCT": "rbl_pct",
                "PERIO_TEETH_LOST": "teeth_lost_perio"}
# Type Concept "EHR". There is no standard "synthetic" type concept; provenance
# is carried by person_source_value and the repo itself.
NOTE_TYPE_DENTAL = 32817


def _visits_from_synthea(csv_dir: Path) -> pd.DataFrame:
    pts = pd.read_csv(csv_dir / "patients.csv", usecols=["Id", "BIRTHDATE", "GENDER"])
    enc = pd.read_csv(csv_dir / "encounters.csv", usecols=["Id", "PATIENT", "START", "DESCRIPTION"])
    dental = enc[enc["DESCRIPTION"].str.contains("dental", case=False, na=False)].copy()
    if dental.empty:  # built-in module names vary across Synthea versions
        dental = enc.copy()
    dental["visit_date"] = pd.to_datetime(dental["START"]).dt.date
    v = dental.merge(pts, left_on="PATIENT", right_on="Id", suffixes=("", "_p"))
    v["age"] = [(d - pd.to_datetime(b).date()).days // 365 for d, b in zip(v["visit_date"], v["BIRTHDATE"])]
    v = v[v["age"] >= 18]
    pid = {s: i + 1 for i, s in enumerate(sorted(v["PATIENT"].unique()))}
    return pd.DataFrame({"person_source_value": v["PATIENT"], "person_id": v["PATIENT"].map(pid),
                         "gender": v["GENDER"], "birth_date": pd.to_datetime(v["BIRTHDATE"]).dt.date,
                         "visit_date": v["visit_date"], "age": v["age"]})


def _visits_generated(n_people: int, rng: random.Random) -> pd.DataFrame:
    rows = []
    for pid in range(1, n_people + 1):
        birth = dt.date(1940, 1, 1) + dt.timedelta(days=rng.randint(0, 365 * 63))
        first = dt.date(2021, 1, 1) + dt.timedelta(days=rng.randint(0, 180))
        for k in range(rng.randint(1, 4)):  # 1-4 recall visits ~6 months apart
            d = first + dt.timedelta(days=182 * k + rng.randint(-20, 20))
            rows.append(dict(person_source_value=f"gen-{pid}", person_id=pid,
                             gender=rng.choice("MF"), birth_date=birth, visit_date=d,
                             age=(d - birth).days // 365))
    df = pd.DataFrame(rows)
    # One gender per person.
    df["gender"] = df.groupby("person_id")["gender"].transform("first")
    return df


def build(out_omop: Path, out_labels: Path, synthea_csv: Path | None = None,
          n_people: int = 300, seed: int = 42, leak_assessment: bool = True) -> pd.DataFrame:
    rng = random.Random(seed)
    if synthea_csv and (synthea_csv / "patients.csv").exists():
        visits, source = _visits_from_synthea(synthea_csv), "synthea"
    else:
        visits, source = _visits_generated(n_people, rng), "generated"
    visits = visits.sort_values(["person_id", "visit_date"]).reset_index(drop=True)
    visits["visit_occurrence_id"] = range(1, len(visits) + 1)

    meas, notes = [], []
    for v in visits.itertuples():
        chart = draw_chart(int(v.age), rng)
        for code, field in CHART_FIELDS.items():
            meas.append(dict(measurement_id=len(meas) + 1, person_id=v.person_id,
                             measurement_concept_id=LOCAL[code], measurement_date=v.visit_date,
                             value_as_number=float(getattr(chart, field)),
                             visit_occurrence_id=v.visit_occurrence_id, measurement_source_value=code))
        text = render_soap_note(chart, seed=seed * 100_003 + v.visit_occurrence_id,
                                leak_assessment=leak_assessment)
        notes.append(dict(note_id=v.visit_occurrence_id, person_id=v.person_id, note_date=v.visit_date,
                          note_type_concept_id=NOTE_TYPE_DENTAL, note_title="Dental SOAP note",
                          note_text=text, visit_occurrence_id=v.visit_occurrence_id,
                          label=label_chart(chart).value,
                          **{f: getattr(chart, f) for f in CHART_FIELDS.values()}))

    out_omop.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)
    person = visits.drop_duplicates("person_id")
    pd.DataFrame({"person_id": person["person_id"],
                  "gender_concept_id": person["gender"].map({"M": 8507, "F": 8532}),
                  "year_of_birth": [d.year for d in person["birth_date"]],
                  "person_source_value": person["person_source_value"]}).to_parquet(out_omop / "person.parquet")
    pd.DataFrame({"visit_occurrence_id": visits["visit_occurrence_id"], "person_id": visits["person_id"],
                  "visit_concept_id": 9202,  # Outpatient Visit
                  "visit_start_date": visits["visit_date"]}).to_parquet(out_omop / "visit_occurrence.parquet")
    pd.DataFrame(meas).to_parquet(out_omop / "measurement.parquet")
    notes_df = pd.DataFrame(notes)
    notes_df.drop(columns=["label", *CHART_FIELDS.values()]).to_parquet(out_omop / "note.parquet")

    labeled = notes_df[["note_id", "person_id", "note_text", "label", *CHART_FIELDS.values()]]
    labeled.to_parquet(out_labels / "labeled_notes.parquet")
    labeled.to_csv(out_labels / "labeled_notes.csv", index=False)
    print(f"source={source} people={person.shape[0]} notes={len(labeled)}")
    print(labeled["label"].value_counts().to_string())
    return labeled
