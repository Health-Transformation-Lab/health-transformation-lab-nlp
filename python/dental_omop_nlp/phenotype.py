"""Method comparison and the rule-based phenotyping algorithm.

Mirrors the study process:

  compare each method against each other   -> agreement_matrix()
  qualitative review (two dental reviewers) -> docs/process.md; outputs feed RULES_V0
  rule-based phenotyping algorithm          -> phenotype_v0()
  quantitative validation                   -> reliability.py (reviewers vs algorithm vs AI)

phenotype_v0 is a placeholder hierarchy so the pipeline runs end to end. The
real rules come out of the qualitative review; edit RULES_V0 and the function,
bump the version, and every downstream number is re-run.
"""

from __future__ import annotations

import itertools

import pandas as pd

from .sources import UNKNOWN

METHODS = ["notes", "exam_form", "proc_codes_completed", "proc_codes_planned",
           "proc_dx_completed", "proc_dx_planned", "probing_chart"]

RULES_V0 = {
    "version": "v0-placeholder",
    # Trust order when sources disagree. Probing chart first: it is the measured
    # evidence the 2017 definitions are written against. Then the clinician's
    # written diagnosis, then diagnosis codes, then the form, then procedures.
    "priority": ["probing_chart", "notes", "proc_dx_completed", "proc_dx_planned",
                 "exam_form", "proc_codes_completed", "proc_codes_planned"],
}


def phenotype_v0(row: pd.Series, rules: dict = RULES_V0) -> tuple[str, str]:
    """Returns (status, method that decided)."""
    for m in rules["priority"]:
        v = row.get(m, UNKNOWN)
        if isinstance(v, str) and v and v != UNKNOWN:
            return v, m
    return UNKNOWN, "none"


def cohen_kappa(a: pd.Series, b: pd.Series) -> float:
    cats = sorted(set(a) | set(b))
    n = len(a)
    if n == 0:
        return float("nan")
    po = (a.values == b.values).mean()
    pe = sum((a == c).mean() * (b == c).mean() for c in cats)
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def agreement_matrix(df: pd.DataFrame, methods: list[str] = METHODS, level: str = "status") -> pd.DataFrame:
    """Pairwise agreement over visits where BOTH methods give an answer.

    level='status'  six classes; level='perio' periodontitis yes/no.
    Returns long format: method_a, method_b, n, pct_agree, kappa.
    """
    rows = []
    for a, b in itertools.combinations(methods, 2):
        both = df[(df[a] != UNKNOWN) & (df[b] != UNKNOWN)]
        x, y = both[a], both[b]
        if level == "perio":
            x, y = x.str.startswith("periodontitis"), y.str.startswith("periodontitis")
        rows.append({"method_a": a, "method_b": b, "n": len(both),
                     "pct_agree": float((x.values == y.values).mean()) if len(both) else float("nan"),
                     "kappa": cohen_kappa(x, y)})
    return pd.DataFrame(rows)


def coverage(df: pd.DataFrame, methods: list[str] = METHODS) -> pd.Series:
    """Share of visits where each method says anything at all."""
    return pd.Series({m: float((df[m] != UNKNOWN).mean()) for m in methods})
