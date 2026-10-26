"""Data quality checks on the structured dental record (spec 005, US4).

Grouped with the harmonized data-quality terms OHDSI's Data Quality Dashboard
uses (Kahn et al. 2016):

    conformance   values in allowed ranges and formats
    completeness  how often each evidence type says anything
    plausibility  believable values (atemporal) and believable change over time
                  (temporal, plausibility.py)

Each check reports rows checked, rows failing and pass rate; conformance and
plausibility checks pass when <= 5% of rows fail (DQD-style threshold, to be
agreed), completeness is reported without a threshold.
"""

from __future__ import annotations

import pandas as pd

from .plausibility import check_history
from .sources import UNKNOWN

THRESHOLD_FAIL = 0.05
RANGES = {"probing_depth_range": ("rec_max_probing_depth_mm", 0, 15),
          "cal_range": ("rec_max_cal_mm", 0, 15),
          "bop_range": ("rec_bop_pct", 0, 100),
          "rbl_range": ("rec_rbl_pct", 0, 100),
          "teeth_lost_range": ("rec_teeth_lost_perio", 0, 32)}
COMPLETENESS = ["notes", "exam_form", "proc_dx_completed", "probing_chart"]
AGE_RANGE = (18, 110)


def _row(check, category, n, fail, threshold=THRESHOLD_FAIL):
    rate = 1 - fail / n if n else float("nan")
    status = "REPORT" if threshold is None else ("PASS" if n == 0 or fail / n <= threshold else "FAIL")
    return {"check": f"{category}:{check}", "category": category, "n_checked": int(n), "n_fail": int(fail),
            "pass_rate": rate, "status": status}


def _checks(v: pd.DataFrame, today: str) -> list[dict]:
    out = []
    ch = v[v["charted"].astype(bool)]
    for name, (col, lo, hi) in RANGES.items():
        x = ch[col].dropna()
        out.append(_row(name, "conformance", len(x), ((x < lo) | (x > hi)).sum()))
    d = pd.to_datetime(v["visit_date"])
    out.append(_row("visit_not_future", "conformance", len(d), (d > pd.Timestamp(today)).sum()))
    for c in COMPLETENESS:
        if c in v:
            out.append(_row(c, "completeness", len(v), (v[c] == UNKNOWN).sum(), threshold=None))
    a = v["age"]
    out.append(_row("age_range", "plausibility", len(a), ((a < AGE_RANGE[0]) | (a > AGE_RANGE[1])).sum()))
    hist = v.rename(columns={"rec_max_cal_mm": "max_cal_mm", "rec_rbl_pct": "rbl_pct",
                             "rec_teeth_lost_perio": "teeth_lost_perio"})
    f = check_history(hist, status_col="probing_chart")
    later = f[f["visit_id"].isin(v.loc[v.duplicated("person_id"), "visit_id"])]   # visits after a person's first
    for flag in ("cal_drop", "rbl_drop", "teeth_regained", "perio_resolved", "stage_drop"):
        out.append(_row(f"temporal_{flag}", "plausibility", len(later), later[flag].sum()))
    return out


def run_checks(visits: pd.DataFrame, today: str, by: str | None = None) -> pd.DataFrame:
    """visits: visits_structured.csv rows. Returns one row per check (and group)."""
    if by is None:
        return pd.DataFrame(_checks(visits, today))
    parts = [pd.DataFrame(_checks(g, today)).assign(**{by: k}) for k, g in visits.groupby(by)]
    return pd.concat(parts, ignore_index=True)
