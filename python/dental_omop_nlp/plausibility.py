"""Temporal plausibility of a patient's record across visits (spec 005, US2).

Each visit is compared with the same person's previous visit that has the value:

    cal_drop        max CAL fell by more than 1.5 mm (beyond probing error; attachment loss
                    doesn't recover without regenerative surgery)
    rbl_drop        radiographic bone loss fell by more than 5 percentage points
    teeth_regained  teeth lost to periodontitis went down
    perio_resolved  periodontitis at an earlier visit, healthy/gingivitis now
                    (2017 classification: a periodontitis patient remains one)
    stage_drop      a lower stage than at an earlier visit

Chart checks use charted visits only; status checks skip 'unknown'. The status can
be any source or the integrated phenotype, so the same checks score how plausible
each method's calls are over time.

r/R/06_validation.R has the R twin; the parity test checks they agree.
"""

from __future__ import annotations

import pandas as pd

from .labels import LABELS
from .telemetry import traced

FLAGS = ["cal_drop", "rbl_drop", "teeth_regained", "perio_resolved", "stage_drop"]
CAL_TOL_MM = 1.5
RBL_TOL_PCT = 5.0


@traced
def check_history(visits: pd.DataFrame, status_col: str = "status") -> pd.DataFrame:
    """visits: visit_id, person_id, visit_date, charted, max_cal_mm, rbl_pct,
    teeth_lost_perio, <status_col>. Returns visit_id, person_id, the FLAGS and any_flag."""
    rows = []
    pid = object()   # one pass over the sorted visits; state resets at each new person
    visits = visits.dropna(subset=["person_id"])   # no person, no history (as groupby did)
    for r in visits.sort_values(["person_id", "visit_date", "visit_id"]).itertuples():
        if r.person_id != pid:
            pid, last_chart, best_rank = r.person_id, None, None
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
            if best_rank is not None and best_rank >= 2:      # periodontitis seen before
                f["perio_resolved"] = rank < 2
                f["stage_drop"] = rank < best_rank
            best_rank = rank if best_rank is None else max(best_rank, rank)
        rows.append({"visit_id": r.visit_id, "person_id": pid, **f})
    out = pd.DataFrame(rows, columns=["visit_id", "person_id", *FLAGS])
    out["any_flag"] = out[FLAGS].any(axis=1)
    return out


@traced
def flag_rates(flags: pd.DataFrame, by: pd.Series | None = None) -> pd.DataFrame:
    """Share of visits with each flag (after a person's first visit), overall or by group."""
    f = flags.copy()
    f["group"] = "all" if by is None else by.reindex(f["visit_id"]).to_numpy()
    return f.groupby("group")[[*FLAGS, "any_flag"]].mean().reset_index()


# Transitions over time (spec 013 G8; Kahn et al. 2016 temporal plausibility). Each visit is paired with
# the same person's first later visit 1-2 years on; pairs with periodontal therapy in between are dropped,
# since only then is an improvement implausible. Statuses are compared on five categories.
FIVE = ["healthy_gingivitis", "periodontitis_stage_1", "periodontitis_stage_2",
        "periodontitis_stage_3", "periodontitis_stage_4"]
MIN_DAYS, MAX_DAYS = 365, 730


def _five(s: str) -> str:
    return "healthy_gingivitis" if s in ("healthy", "gingivitis") else s


@traced
def transition_pairs(visits: pd.DataFrame, status_col: str = "status",
                     min_days: int = MIN_DAYS, max_days: int = MAX_DAYS) -> pd.DataFrame:
    """visits: visit_id, person_id, visit_date, treated_before, <status_col>. Returns one row per
    pair: person_id, visit_id, next_visit_id, days, from_status, to_status, change (better/same/worse)."""
    v = visits[visits[status_col].isin(LABELS)].copy()
    v["date"] = pd.to_datetime(v["visit_date"])
    v["five"] = v[status_col].map(_five)
    rows = []
    for pid, g in v.sort_values(["person_id", "date", "visit_id"]).groupby("person_id", sort=False):
        g = list(g.itertuples())
        for i, a in enumerate(g):
            for b in g[i + 1:]:
                days = (b.date - a.date).days
                if days > max_days:
                    break
                if days < min_days:
                    continue
                if bool(b.treated_before) and not bool(a.treated_before):
                    break                              # therapy between the two visits
                ra, rb = FIVE.index(a.five), FIVE.index(b.five)
                rows.append({"person_id": pid, "visit_id": a.visit_id, "next_visit_id": b.visit_id,
                             "days": days, "from_status": a.five, "to_status": b.five,
                             "change": "better" if rb < ra else "worse" if rb > ra else "same"})
                break
    return pd.DataFrame(rows, columns=["person_id", "visit_id", "next_visit_id", "days",
                                       "from_status", "to_status", "change"])


@traced
def transition_summary(pairs: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Five-by-five counts (rows: earlier visit) and the share of pairs better / same / worse."""
    m = pd.crosstab(pd.Categorical(pairs["from_status"], FIVE), pd.Categorical(pairs["to_status"], FIVE),
                    dropna=False)
    m.index.name, m.columns.name = "from_status", "to_status"
    n = len(pairs)
    shares = {"pairs": n, **{c: float((pairs["change"] == c).mean()) if n else 0.0
                             for c in ("better", "same", "worse")}}
    return m, shares
