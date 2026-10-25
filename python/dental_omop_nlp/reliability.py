"""Quantitative validation: reviewer reliability, and how the algorithm and AI
compare with the reviewers.

    inter-reviewer      Fleiss' kappa (nominal) across all reviewers who staged
                        the same charts; pairwise Cohen's kappa; quadratic
                        weighted kappa treating status as ordinal
                        (healthy < gingivitis < stage I < ... < stage IV)
    consensus           majority vote per visit (ties → 'no_consensus')
    method vs reviewers each method / algorithm / AI model vs consensus, and
                        vs each reviewer (is it inside the reviewers' spread?).
                        Agreement is over visits where the method gives an
                        answer; `coverage` says how often that is. Report both:
                        a source that is right when present but usually absent
                        is a different finding from one that is often wrong.

r/R/04_reliability.R computes the same numbers in R; the parity test checks.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from .labels import Status
from .phenotype import cohen_kappa

ORDER = [s.value for s in Status]


def fleiss_kappa(wide: pd.DataFrame) -> float:
    """wide: rows = visits, cols = reviewers, values = category. Rows with any NA dropped."""
    w = wide.dropna()
    cats = sorted(pd.unique(w.values.ravel()))
    n = w.shape[1]
    counts = np.stack([(w.values == c).sum(axis=1) for c in cats], axis=1)  # N x k
    p_j = counts.sum(axis=0) / counts.sum()
    P_i = ((counts * (counts - 1)).sum(axis=1)) / (n * (n - 1))
    P_bar, P_e = P_i.mean(), (p_j ** 2).sum()
    return float((P_bar - P_e) / (1 - P_e))


def weighted_kappa(a: pd.Series, b: pd.Series, order: list[str] = ORDER) -> float:
    """Quadratic-weighted Cohen's kappa over ordinal statuses; other values dropped."""
    keep = a.isin(order) & b.isin(order)
    x = a[keep].map(order.index).to_numpy()
    y = b[keep].map(order.index).to_numpy()
    k = len(order)
    O = np.zeros((k, k))
    for i, j in zip(x, y):
        O[i, j] += 1
    if O.sum() == 0:
        return float("nan")
    W = np.array([[(i - j) ** 2 / (k - 1) ** 2 for j in range(k)] for i in range(k)])
    E = np.outer(O.sum(axis=1), O.sum(axis=0)) / O.sum()
    return float(1 - (W * O).sum() / (W * E).sum())


def consensus(wide: pd.DataFrame) -> pd.Series:
    def vote(row):
        vc = row.dropna().value_counts()
        if vc.empty or (len(vc) > 1 and vc.iloc[0] == vc.iloc[1]):
            return "no_consensus"
        return vc.index[0]
    return wide.apply(vote, axis=1).rename("consensus")


def _kappa_where_both(a: pd.Series, b: pd.Series) -> float:
    ok = a.isin(ORDER) & b.isin(ORDER)
    return cohen_kappa(a[ok], b[ok])


def reliability_report(labels: pd.DataFrame, key: pd.DataFrame, compare: dict[str, pd.Series]) -> dict:
    """labels: reviewer_labels.csv; key: review_key.csv indexed by visit_id;
    compare: name -> Series(status) indexed by visit_id (methods, algorithm, AI)."""
    wide = labels.pivot_table(index="visit_id", columns="reviewer", values="status", aggfunc="first")
    cons = consensus(wide)
    pair = [{"a": a, "b": b, "kappa": cohen_kappa(wide[a].dropna(), wide[b].reindex(wide[a].dropna().index)),
             "weighted_kappa": weighted_kappa(wide[a], wide[b])}
            for a, b in itertools.combinations(wide.columns, 2)]
    rows = []
    for name, s in {"generator_chart_truth": key["truth_status"], **compare}.items():
        s = s.reindex(cons.index)
        has = s.isin(ORDER)                  # the method said something about status
        ok = cons.isin(ORDER) & has
        rows.append({"method": name, "coverage": float(has.mean()), "n": int(ok.sum()),
                     "pct_agree_consensus": float((s[ok] == cons[ok]).mean()),
                     "kappa_vs_consensus": cohen_kappa(s[ok], cons[ok]),
                     "weighted_kappa_vs_consensus": weighted_kappa(s[ok], cons[ok]),
                     "mean_kappa_vs_each_reviewer": float(np.nanmean(
                         [_kappa_where_both(s, wide[r]) for r in wide.columns]))})
    return {"n_visits": int(wide.shape[0]), "n_reviewers": int(wide.shape[1]),
            "fleiss_kappa": fleiss_kappa(wide),
            "consensus_reached": float(cons.isin(ORDER).mean()),
            "pairwise": pd.DataFrame(pair), "methods": pd.DataFrame(rows), "consensus": cons}
