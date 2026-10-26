"""Predicting periodontal progression from the record (spec 005, US5).

Unit: a pair of consecutive visits of one person where both have a known
phenotype. Outcome: the next visit's phenotype is a higher category (onset of
periodontitis or a higher stage). Features come from the current visit only.

Model: standardized logistic regression; people split 70/30 by seed so no
person is in both. Reported: AUROC on held-out pairs with a bootstrap 95% CI,
and permutation importance (drop in AUROC when a feature is shuffled).

The generator uses smoking, diabetes, existing disease and therapy for
progression, but over <= 3 years of history only existing disease and therapy
show up in the importance ranking (action item D3). The point here is the pipeline; on real data, compare the ranking with
established risk factors (the AAP grade modifiers are smoking and diabetes).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .labels import LABELS

RANK = {**{s: i for i, s in enumerate(LABELS)}, "healthy_gingivitis": 0}
FEATURES = ["age", "smoker_1_9", "smoker_10plus", "diabetes", "treated_before", "charted", "current_rank",
            "max_probing_depth_mm", "bop_pct", "max_cal_mm", "rbl_pct", "teeth_lost_perio"]
_CHART = {"rec_max_probing_depth_mm": "max_probing_depth_mm", "rec_bop_pct": "bop_pct",
          "rec_max_cal_mm": "max_cal_mm", "rec_rbl_pct": "rbl_pct", "rec_teeth_lost_perio": "teeth_lost_perio"}


def make_pairs(visits: pd.DataFrame, status_col: str) -> pd.DataFrame:
    v = visits[visits[status_col].isin(RANK)].sort_values(["person_id", "visit_date"]).copy()
    v["next_rank"] = v.groupby("person_id")[status_col].shift(-1).map(RANK)
    v = v[v["next_rank"].notna()].copy()
    v["current_rank"] = v[status_col].map(RANK)
    v["y_progress"] = (v["next_rank"] > v["current_rank"]).astype(int)
    v["smoker_1_9"] = ((v["cigarettes_per_day"] > 0) & (v["cigarettes_per_day"] < 10)).astype(int)
    v["smoker_10plus"] = (v["cigarettes_per_day"] >= 10).astype(int)
    v = v.rename(columns=_CHART)
    for c in _CHART.values():
        v[c] = v[c].astype(float)
        v[c] = v[c].fillna(v[c].median() if v[c].notna().any() else 0.0)   # charted=0 marks the fill
    for c in ("diabetes", "treated_before", "charted"):
        v[c] = v[c].astype(bool).astype(int)
    return v[["visit_id", "person_id", *FEATURES, "y_progress"]].reset_index(drop=True)


def train_eval(pairs: pd.DataFrame, seed: int = 0, n_boot: int = 500, test_share: float = 0.3) -> dict:
    rng = np.random.default_rng(seed)
    people = pairs["person_id"].unique()
    test_people = set(rng.choice(people, size=int(len(people) * test_share), replace=False))
    te = pairs["person_id"].isin(test_people)
    X, y = pairs[FEATURES], pairs["y_progress"]
    m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(X[~te], y[~te])
    p = m.predict_proba(X[te])[:, 1]
    yt = y[te].to_numpy()
    auc = roc_auc_score(yt, p)
    boots = []
    for _ in range(n_boot):
        i = rng.integers(0, len(yt), len(yt))
        if yt[i].min() != yt[i].max():
            boots.append(roc_auc_score(yt[i], p[i]))
    lo, hi = (np.percentile(boots, [2.5, 97.5]) if boots else (np.nan, np.nan))
    pi = permutation_importance(m, X[te], yt, scoring="roc_auc", n_repeats=20, random_state=seed)
    coef = m[-1].coef_[0]
    imp = pd.DataFrame({"feature": FEATURES, "importance": pi.importances_mean, "importance_sd": pi.importances_std,
                        "std_coef": coef}).sort_values("importance", ascending=False).reset_index(drop=True)
    return {"n_pairs_train": int((~te).sum()), "n_pairs_test": int(te.sum()), "progress_rate": float(y.mean()),
            "auroc": float(auc), "auroc_ci_low": float(lo), "auroc_ci_high": float(hi), "importance": imp}
