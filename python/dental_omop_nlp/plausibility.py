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

FLAGS = ["cal_drop", "rbl_drop", "teeth_regained", "perio_resolved", "stage_drop"]
CAL_TOL_MM = 1.5
RBL_TOL_PCT = 5.0


def check_history(visits: pd.DataFrame, status_col: str = "status") -> pd.DataFrame:
    """visits: visit_id, person_id, visit_date, charted, max_cal_mm, rbl_pct,
    teeth_lost_perio, <status_col>. Returns visit_id, person_id, the FLAGS and any_flag."""
    rows = []
    pid = object()   # one pass over the sorted visits; state resets at each new person
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


def flag_rates(flags: pd.DataFrame, by: pd.Series | None = None) -> pd.DataFrame:
    """Share of visits with each flag (after a person's first visit), overall or by group."""
    f = flags.copy()
    f["group"] = "all" if by is None else by.reindex(f["visit_id"]).to_numpy()
    return f.groupby("group")[[*FLAGS, "any_flag"]].mean().reset_index()
