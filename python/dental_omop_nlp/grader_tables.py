"""The tables the two graders read (spec 018), one DataFrame per gold table, built from committed CSVs.

    dq_tables   the EHR DQ grader: data-quality checks, completeness, prevalence, temporal plausibility,
                transitions, concordance, per-visit evidence with its truth (statuses only, never note text)

Every row carries `source_files` and `sha256` (of those files, together), so a table says which version of the
results it holds. The Load results job overwrites each table from these on every run.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from .telemetry import traced

STATUS_ORDER = ["healthy_gingivitis", "periodontitis_stage_1", "periodontitis_stage_2", "periodontitis_stage_3",
                "periodontitis_stage_4"]
# the evidence sources the DQ grader scores against the truth, in the study's terms (evidence_rules.md)
EVIDENCE = ["notes", "exam_form", "proc_dx_completed", "proc_dx_planned", "probing_chart", "algorithm_v0",
            "algorithm_design"]


def _with_provenance(df: pd.DataFrame, folder: Path, files: list[str]) -> pd.DataFrame:
    h = hashlib.sha256()
    for f in files:
        h.update((Path(folder) / f).read_bytes())
    return df.reset_index(drop=True).assign(source_files=",".join(files), sha256=h.hexdigest())


def _read(folder: Path, f: str) -> pd.DataFrame:
    return pd.read_csv(Path(folder) / f)


@traced
def dq_tables(datasets_dir: Path) -> dict[str, pd.DataFrame]:
    """Every dq_* table of spec 018 US1, from data/datasets/ (DATASETS_DIR)."""
    d = Path(datasets_dir)
    out = {}

    f = ["data_quality/dq_overall.csv", "data_quality/dq_by_clinic.csv"]
    overall = _read(d, f[0]).assign(clinic="All")
    by_clinic = _read(d, f[1]).assign(clinic=lambda x: x.clinic_id.astype(int).astype(str)).drop(columns="clinic_id")
    checks = pd.concat([overall, by_clinic], ignore_index=True).rename(columns={"check": "check_name"})
    out["dq_checks"] = _with_provenance(checks, d, f)   # `check` and `column` are reserved words in SQL

    f = ["data_quality/completeness_columns.csv"]
    out["dq_completeness"] = _with_provenance(_read(d, f[0]).rename(columns={"column": "evidence_column"}), d, f)

    f = ["prevalence/prevalence_by_clinic.csv", "data_quality/prevalence_by_scale.csv"]
    clinic = _read(d, f[0]).rename(columns={"n_people": "n"}).assign(
        level="clinic", group_name=lambda x: x.clinic_id.astype(int).astype(str))
    scale = _read(d, f[1]).rename(columns={"status_col": "method", "scale": "group_name", "n_known": "n"}).assign(
        level="scale")
    cols = ["method", "level", "group_name", "n", "periodontitis", "periodontitis_ci_low", "periodontitis_ci_high",
            "stage3_4"]
    out["dq_prevalence"] = _with_provenance(pd.concat([clinic, scale], ignore_index=True).reindex(columns=cols), d, f)

    f = ["data_quality/temporal_by_method.csv", "data_quality/transitions_by_method.csv"]
    out["dq_temporal"] = _with_provenance(_read(d, f[0]).merge(_read(d, f[1]), on="method", how="outer"), d, f)

    f = ["data_quality/transitions_algorithm_design.csv"]
    m = _read(d, f[0]).set_index("from_status")
    long = m.stack().rename("n").reset_index().rename(columns={"level_1": "to_status"})
    long["row_pct"] = 100 * long.n / long.groupby("from_status").n.transform("sum")
    rank = {s: i for i, s in enumerate(STATUS_ORDER)}
    step = long.to_status.map(rank) - long.from_status.map(rank)
    long["direction"] = step.map(lambda s: "worse" if s > 0 else "better" if s < 0 else "same")
    long.insert(0, "method", "algorithm_design")
    out["dq_transitions"] = _with_provenance(long, d, f)

    f = ["method_agreement.csv"]
    out["dq_concordance"] = _with_provenance(_read(d, f[0]), d, f)

    f = ["visits_structured.csv", "answer_key/visits_truth.csv"]
    v = _read(d, f[0])[["visit_id", "person_id", "clinic_id", "visit_date", "visit_seq", "in_review", *EVIDENCE]]
    truth = _read(d, f[1])[["visit_id", "truth_status"]]
    v = v.merge(truth, on="visit_id", validate="one_to_one").assign(clinic=lambda x: x.clinic_id.astype(str))
    out["dq_visits"] = _with_provenance(v.drop(columns="clinic_id"), d, f)

    f = ["data_quality/injected_error_recall.csv"]
    out["dq_injected_errors"] = _with_provenance(_read(d, f[0]), d, f)
    return out
