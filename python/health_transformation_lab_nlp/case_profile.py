"""Case profiles for the synthetic study's visits (spec 026, US1).

Every visit's structured evidence laid out the same way, grouped into the categories KEEPER uses for case
review (Schuemie, Ostropolets et al., npj Digit Med 2025; docs/rag_and_vocabulary.md, R6), adapted to
periodontal records. A reviewer, Genie or the chart review agent reads one profile instead of a dozen columns.

Structured values only, never note text: `notes` in visits_structured.csv is the note reader's status. A value
the record lacks reads "not recorded", never left out or filled in. Synthetic data only.

We find gum disease in records; we don't diagnose (AGENTS.md, "Words"). The recorded diagnosis codes here are
what the synthetic dentist recorded.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import plausibility
from .telemetry import traced

NOT_RECORDED = "not recorded"
NOT_TAKEN = "not taken"
NO_LATER_VISIT = "no later visit"
NEXT_CODE = "next visit's recorded code"
NEXT_FLAGS = "next visit's plausibility flags"

# (category, item, source column in visits_structured.csv or None when derived, unit), in display order
PROFILE_ITEMS: list[tuple[str, str, str | None, str]] = [
    ("Demographics", "age", "age", "years"),
    ("Demographics", "clinic", "clinic_id", ""),
    ("Presentation", "recorded diagnosis code, completed", "proc_dx_completed", ""),
    ("Presentation", "recorded diagnosis code, planned", "proc_dx_planned", ""),
    ("Presentation", "exam form", "exam_form", ""),
    ("Visit context", "visit number for the patient", "visit_seq", ""),   # shown from 1; visit_seq starts at 0
    ("Visit context", "probing chart taken", "charted", ""),
    ("Visit context", "treated before", "treated_before", ""),
    ("Measurements", "max probing depth", "rec_max_probing_depth_mm", "mm"),
    ("Measurements", "bleeding on probing", "rec_bop_pct", "%"),
    ("Measurements", "max attachment loss (CAL)", "rec_max_cal_mm", "mm"),
    ("Measurements", "bone loss", "rec_rbl_pct", "%"),
    ("Measurements", "teeth lost to periodontitis", "rec_teeth_lost_perio", "teeth"),
    ("Measurements", "teeth involved", "rec_pct_teeth_involved", "%"),
    ("Tests and imaging", "probing chart reading", "probing_chart", ""),
    ("Tests and imaging", "radiograph AI reading", "radiograph_ai", ""),
    ("Risk factors", "cigarettes per day", "cigarettes_per_day", ""),
    ("Risk factors", "diabetes", "diabetes", ""),
    ("Risk factors", "HbA1c", "hba1c", "%"),
    ("Treatment", "status from periodontal procedure codes, completed", "proc_codes_completed", ""),
    ("Treatment", "status from periodontal procedure codes, planned", "proc_codes_planned", ""),
    ("Other readings", "note reader", "notes", ""),
    ("Other readings", "rules, gum measurements first", "algorithm_v0", ""),
    ("Other readings", "rules in the study design's order", "algorithm_design", ""),
    ("After the visit", NEXT_CODE, None, ""),
    ("After the visit", NEXT_FLAGS, None, ""),
]
CATEGORIES = list(dict.fromkeys(cat for cat, *_ in PROFILE_ITEMS))


def _shown(value) -> str:
    """A value as the profile shows it: "not recorded" when missing or unknown, yes/no, numbers without trailing
    zeros, statuses as their code. Python, numpy and pandas scalars all show the same."""
    if not isinstance(value, str) and pd.isna(value):
        return NOT_RECORDED
    if value == "unknown":
        return NOT_RECORDED
    if isinstance(value, (bool, np.bool_)):
        return "yes" if value else "no"
    if isinstance(value, (int, float, np.number)):
        return f"{float(value):g}"
    return str(value)


@traced
def history_frame(visits: pd.DataFrame) -> pd.DataFrame:
    """The columns plausibility.check_history reads, from visits_structured.csv rows (as 20_data_quality does)."""
    return visits.rename(columns={"rec_max_cal_mm": "max_cal_mm", "rec_rbl_pct": "rbl_pct",
                                  "rec_teeth_lost_perio": "teeth_lost_perio"})


def _after(visits: pd.DataFrame) -> pd.DataFrame:
    """Per visit: the same patient's next visit's recorded code and the plausibility checks that visit fails."""
    flags = plausibility.check_history(history_frame(visits), "proc_dx_completed").set_index("visit_id")
    failed = flags[plausibility.FLAGS].apply(lambda r: ", ".join(f for f in plausibility.FLAGS if r[f]) or "none",
                                             axis=1)
    v = visits.sort_values(["person_id", "visit_date", "visit_id"])   # the order check_history uses
    nxt = v.groupby("person_id").visit_id.shift(-1)
    out = pd.DataFrame({"visit_id": v.visit_id.to_numpy(), "next_id": nxt.to_numpy()})
    code = visits.set_index("visit_id").proc_dx_completed
    has_next = out.next_id.notna()
    out[NEXT_CODE] = NO_LATER_VISIT
    out[NEXT_FLAGS] = NO_LATER_VISIT
    ids = out.loc[has_next, "next_id"].astype("int64")
    out.loc[has_next, NEXT_CODE] = [_shown(c) for c in code.loc[ids]]
    out.loc[has_next, NEXT_FLAGS] = failed.loc[ids].to_numpy()
    return out.set_index("visit_id")


@traced
def build_profiles(visits: pd.DataFrame) -> pd.DataFrame:
    """visits: visits_structured.csv rows. Returns the profiles in long form, one row per (visit, item):
    visit_id, category, category_order, item, item_order, value, unit."""
    after = _after(visits)
    order = {c: i + 1 for i, c in enumerate(CATEGORIES)}
    rows = []
    visits = visits.astype(object).where(visits.notna(), None)   # one scalar type, whatever the dtypes
    for r in visits.itertuples(index=False):
        rec = r._asdict()
        for i, (cat, item, col, unit) in enumerate(PROFILE_ITEMS, start=1):
            if col is None:
                value = after.at[r.visit_id, item]
            elif col == "probing_chart" and not rec["charted"]:
                value = NOT_TAKEN
            elif col == "visit_seq":
                value = _shown(rec[col] + 1)
            else:
                value = _shown(rec[col])
            rows.append({"visit_id": r.visit_id, "category": cat, "category_order": order[cat], "item": item,
                         "item_order": i, "value": value, "unit": unit if value not in
                         (NOT_RECORDED, NOT_TAKEN, NO_LATER_VISIT) else ""})
    return pd.DataFrame(rows, columns=["visit_id", "category", "category_order", "item", "item_order", "value",
                                       "unit"])
