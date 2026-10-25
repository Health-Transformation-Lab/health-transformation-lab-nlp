"""Build the study datasets: training set, chart-review set, answer key.

One synthetic population, split by person:

  train      every visit of the training people. De-identified note text,
             labelled by the generator. This is what the AI model learns from.
  review     ONE visit per review person (independent charts), stratified so
             rare statuses are represented. Every source for the visit,
             de-identified, packaged as Label Studio tasks. Reviewers stage
             these; nobody sees the generator's answer.
  answer key generator truth, each method's reading, the v0 algorithm. Kept
             apart from the tasks; used only after review to score everyone.

Raw notes with fake PHI are written under data/raw/ (gitignored), standing in
for the secure zone. Only de-identified text that passes the leak gate leaves.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pandas as pd

from .build import _visits_generated
from .clinical_notes import render_clinical_note
from .deid import deidentify, leak_check, residual_scan, score_deid
from .labels import PerioChart, Status, extent_of, grade_of, label_chart
from .note_reader import read_note
from .phenotype import RULES_V0, agreement_matrix, coverage, phenotype_v0
from .phi import fake_person, fake_provider
from .sources import READERS, UNKNOWN, generate_sources
from .synthetic import draw_chart, draw_pct_teeth_involved, draw_risk

REVIEW_STRATA = {  # target share of the review set; rare classes oversampled
    "healthy": 0.15, "gingivitis": 0.20, "periodontitis_stage_1": 0.17,
    "periodontitis_stage_2": 0.18, "periodontitis_stage_3": 0.18, "periodontitis_stage_4": 0.12,
}


def probing_chart_text(c: PerioChart) -> str:
    return (f"Max PD {c.max_probing_depth_mm:.0f} mm | BOP {c.bop_pct:.0f}% | "
            f"Max interproximal CAL {c.max_cal_mm:.0f} mm | RBL {c.rbl_pct:.0f}% | "
            f"Teeth lost to perio: {c.teeth_lost_perio}")


CHARTED_SHARE = 0.8         # visits with a full probing chart (Patel 2020: ~80%)
CLINICIAN_DISAGREES = 0.25   # share of visits where the written dx is one step off the chart


def _clinician_call(status: Status, rng: random.Random) -> Status:
    if rng.random() >= CLINICIAN_DISAGREES:
        return status
    order = list(Status)
    i = order.index(status)
    return order[min(max(i + rng.choice([-1, 1]), 0), len(order) - 1)]


def generate_visits(n_people: int, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    visits = _visits_generated(n_people, rng).sort_values(["person_id", "visit_date"]).reset_index(drop=True)
    people = {pid: (fake_person(rng, g.iloc[0]["birth_date"]), draw_risk(rng))
              for pid, g in visits.groupby("person_id")}
    rows, prev = [], {}
    for i, v in enumerate(visits.itertuples(), start=1):
        person, risk = people[v.person_id]
        chart = draw_chart(int(v.age), rng)
        status = label_chart(chart)
        grade = grade_of(status, chart.rbl_pct, int(v.age), risk.cigarettes_per_day, risk.hba1c)
        extent = extent_of(status, draw_pct_teeth_involved(chart, rng))
        stated = _clinician_call(status, rng)
        text, phi, meta = render_clinical_note(chart, status, grade, extent, risk, person,
                                               fake_provider(rng), v.visit_date, rng, prev.get(v.person_id),
                                               stated_status=stated)
        prev[v.person_id] = v.visit_date
        rows.append(dict(visit_id=i, person_id=v.person_id, visit_date=v.visit_date, age=int(v.age),
                         note_raw=text, phi_spans=json.dumps(phi), **meta,
                         charted=(charted := rng.random() < CHARTED_SHARE),
                         probing_chart_text=probing_chart_text(chart) if charted else "(not charted at this visit)",
                         truth_status=status.value, truth_grade=grade, truth_extent=extent,
                         **{k: getattr(chart, k) for k in ("max_probing_depth_mm", "bop_pct", "max_cal_mm",
                                                           "rbl_pct", "teeth_lost_perio")},
                         **generate_sources(status, extent, rng)))
    return pd.DataFrame(rows)


def apply_deid(df: pd.DataFrame, engine: str = "regex") -> tuple[pd.DataFrame, pd.DataFrame]:
    out, report = [], []
    for r in df.itertuples():
        phi = json.loads(r.phi_spans)
        text, found = deidentify(r.note_raw, engine)
        leaks = leak_check(text, phi)
        s = score_deid(r.note_raw, phi, found)
        report.append({"visit_id": r.visit_id, **s, "leaked_values": len(leaks),
                       "residual_flags": len(residual_scan(text.replace("[", "").replace("]", "")))})
        out.append({"visit_id": r.visit_id, "note_text": text, "deid_passed": not leaks})
    return df.merge(pd.DataFrame(out), on="visit_id"), pd.DataFrame(report)


def read_methods(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["notes"] = [read_note(t) for t in df["note_text"]]
    for col, reader in READERS.items():
        df[col] = [reader(v) for v in df[col + "_raw"]]
    # The chart IS the measured evidence, when it was done. Patel (2020) found
    # charting findings present for ~80% of patients in a real EDR.
    df["probing_chart"] = [ts if charted else UNKNOWN for ts, charted in zip(df["truth_status"], df["charted"])]
    pa = [phenotype_v0(r) for _, r in df.iterrows()]
    df["algorithm_v0"] = [p[0] for p in pa]
    df["algorithm_v0_decided_by"] = [p[1] for p in pa]
    return df


def pick_review(df: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    """One visit per person (latest), stratified by truth status."""
    last = df.sort_values("visit_date").groupby("person_id").tail(1)
    picks = []
    for status, share in REVIEW_STRATA.items():
        pool = last[last["truth_status"] == status]
        picks.append(pool.sample(min(len(pool), round(n * share)), random_state=seed))
    return pd.concat(picks).sample(frac=1, random_state=seed)


def label_studio_tasks(review: pd.DataFrame) -> list[dict]:
    return [{"data": {
        "visit_id": int(r.visit_id),
        "note": r.note_text,
        "exam_form": r.exam_form_raw or "(none)",
        "proc_codes_completed": r.proc_codes_completed_raw or "(none)",
        "proc_codes_planned": r.proc_codes_planned_raw or "(none)",
        "proc_dx_completed": r.proc_dx_completed_raw or "(none)",
        "proc_dx_planned": r.proc_dx_planned_raw or "(none)",
        "probing_chart": r.probing_chart_text,
        "age": int(r.age),
    }} for r in review.itertuples()]


def build_study(out_dir: Path, raw_dir: Path, n_people: int = 1200, review_n: int = 240,
                seed: int = 42, engine: str = "regex") -> dict:
    df = generate_visits(n_people, seed)
    for c in READERS:
        df = df.rename(columns={c: c + "_raw"})
    raw_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(raw_dir / "visits_with_fake_phi.parquet")

    df, deid_report = apply_deid(df, engine)
    blocked = df[~df["deid_passed"]]
    df = df[df["deid_passed"]].drop(columns=["note_raw", "phi_spans"])  # nothing with PHI past here
    df = read_methods(df)

    review = pick_review(df, review_n, seed)
    train = df[~df["person_id"].isin(review["person_id"])]

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "answer_key").mkdir(exist_ok=True)
    train[["visit_id", "person_id", "note_text", "truth_status", "truth_grade", "truth_extent", "stated_status"]] \
        .rename(columns={"truth_status": "label", "truth_grade": "grade", "truth_extent": "extent"}) \
        .assign(label_source="generator").to_csv(out_dir / "train.csv", index=False)
    (out_dir / "review_tasks.json").write_text(json.dumps(label_studio_tasks(review), indent=1))
    key_cols = ["visit_id", "person_id", "age", "truth_status", "truth_grade", "truth_extent",
                "style", "numeric", "dx_scheme", "dx_pattern", "copy_forward", "stated_status", "notes", *READERS, "probing_chart",
                "algorithm_v0", "algorithm_v0_decided_by", "note_text"]
    review[key_cols].to_csv(out_dir / "answer_key" / "review_key.csv", index=False)
    methods = ["notes", *READERS, "probing_chart"]
    agree = pd.concat([agreement_matrix(df, methods, "status").assign(level="status"),
                       agreement_matrix(df, methods, "perio").assign(level="perio")])
    agree.to_csv(out_dir / "method_agreement.csv", index=False)
    coverage(df, methods).rename("coverage").to_csv(out_dir / "method_coverage.csv")
    deid_report.to_csv(out_dir / "deid_report.csv", index=False)

    tot = deid_report[["phi_chars", "phi_chars_removed", "non_phi_chars_removed"]].sum()
    return {"visits": len(df) + len(blocked), "blocked_by_leak_gate": len(blocked),
            "train_visits": len(train), "train_people": train["person_id"].nunique(),
            "review_visits": len(review), "deid_engine": engine,
            "deid_char_recall": round(tot.phi_chars_removed / tot.phi_chars, 4),
            "deid_non_phi_chars_removed": int(tot.non_phi_chars_removed),
            "algorithm": RULES_V0["version"],
            "review_status_mix": review["truth_status"].value_counts().to_dict()}


def build_corpus_sample(n_people: int, seed: int, engine: str = "regex") -> pd.DataFrame:
    """A de-identified stand-in for the full corpus, for timing and judging.

    Returns visit_id, note_text and (for simulated judging ONLY) truth_status.
    A real corpus has no truth column; nothing downstream may use it except
    the simulated judge backend.
    """
    df = generate_visits(n_people, seed)
    for c in READERS:
        df = df.rename(columns={c: c + "_raw"})
    df, _ = apply_deid(df, engine)
    df = df[df["deid_passed"]]
    return df[["visit_id", "person_id", "note_text", "truth_status"]].reset_index(drop=True)
