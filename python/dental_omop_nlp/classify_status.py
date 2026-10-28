"""Periodontal status from the recorded chart with gradient-boosted trees, explained with SHAP (spec 013 G10).

Unit: a charted visit with a known status. Features: the recorded chart plus age, smoking, diabetes, HbA1c
and prior treatment. Two schemes: 5-level (healthy+gingivitis, stage 1-4) and 3-level (healthy+gingivitis,
stage 1-2, stage 3-4). Design after Patel et al. 2022 (Front Artif Intell, doi 10.3389/frai.2022.979525):
XGBoost, 80/20 split (here by person), 5-fold cross-validation for the hyperparameters, one-vs-rest metrics.

SHAP: exact TreeSHAP computed by XGBoost itself (pred_contribs), the algorithm of Lundberg et al. 2020 that
the `shap` package uses for trees. For each held-out visit and class, the values plus a bias add up to the
model's margin (log-odds) for that class. Each feature carries its role in the 2017 AAP/EFP classification
(Tonetti, Greenwell & Kornman 2018), so the ranking can be read against it.

Synthetic data: the labels come from the AAP rules applied to the same chart, so stage criteria should
explain most of the model and grade modifiers little. That checks the pipeline; it finds nothing about
real patients. Needs the `ml` extra (xgboost).
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.utils.class_weight import compute_sample_weight

from .labels import LABELS
from .telemetry import traced

FEATURES = ["max_probing_depth_mm", "bop_pct", "max_cal_mm", "rbl_pct", "teeth_lost_perio", "pct_teeth_involved",
            "age", "smoker_1_9", "smoker_10plus", "diabetes", "hba1c", "treated_before"]
_CHART = {"rec_max_probing_depth_mm": "max_probing_depth_mm", "rec_bop_pct": "bop_pct",
          "rec_max_cal_mm": "max_cal_mm", "rec_rbl_pct": "rbl_pct", "rec_teeth_lost_perio": "teeth_lost_perio",
          "rec_pct_teeth_involved": "pct_teeth_involved"}
ROLES = ("stage", "gingivitis", "extent", "grade", "none")
# Role in the 2017 AAP/EFP classification (Tonetti, Greenwell & Kornman 2018; docs/staging_grading.md).
# Age enters grade through % bone loss / age; probing depth is a stage complexity factor.
AAP_ROLE = {"max_cal_mm": "stage", "rbl_pct": "stage", "teeth_lost_perio": "stage", "max_probing_depth_mm": "stage",
            "bop_pct": "gingivitis", "pct_teeth_involved": "extent", "age": "grade", "smoker_1_9": "grade",
            "smoker_10plus": "grade", "diabetes": "grade", "hba1c": "grade", "treated_before": "none"}

SCHEMES = {
    "5level": {"healthy": 0, "gingivitis": 0, "periodontitis_stage_1": 1, "periodontitis_stage_2": 2,
               "periodontitis_stage_3": 3, "periodontitis_stage_4": 4},
    "3level": {"healthy": 0, "gingivitis": 0, "periodontitis_stage_1": 1, "periodontitis_stage_2": 1,
               "periodontitis_stage_3": 2, "periodontitis_stage_4": 2},
}
CLASS_NAMES = {"5level": ["healthy_gingivitis", "stage_1", "stage_2", "stage_3", "stage_4"],
               "3level": ["healthy_gingivitis", "stage_1_2", "stage_3_4"]}
GRID = {"max_depth": [3, 5], "learning_rate": [0.05, 0.2], "reg_lambda": [1.0, 10.0], "min_child_weight": [1, 5],
        "class_weight": [None, "balanced"]}
N_TREES = 200
assert set(SCHEMES["5level"]) == set(LABELS)


@traced
def features(visits: pd.DataFrame, outcome: str, scheme: str) -> pd.DataFrame:
    """Charted visits with a known status: one row each, the features and the class index `y`."""
    v = visits[visits["charted"].astype(bool) & visits[outcome].isin(LABELS)].rename(columns=_CHART).copy()
    v["smoker_1_9"] = ((v["cigarettes_per_day"] > 0) & (v["cigarettes_per_day"] < 10)).astype(int)
    v["smoker_10plus"] = (v["cigarettes_per_day"] >= 10).astype(int)
    for c in ("diabetes", "treated_before"):
        v[c] = v[c].astype(bool).astype(int)
    v["y"] = v[outcome].map(SCHEMES[scheme])
    v[FEATURES] = v[FEATURES].astype(float)                 # hba1c stays NaN when not measured: trees route it
    return v[["visit_id", "person_id", *FEATURES, "y"]].reset_index(drop=True)


@traced
def split_people(f: pd.DataFrame, seed: int = 0, test_share: float = 0.2) -> np.ndarray:
    """True for held-out rows: a random `test_share` of people, so no person is in both."""
    people = np.sort(f["person_id"].unique())
    test = np.random.default_rng(seed).choice(people, size=round(len(people) * test_share), replace=False)
    return f["person_id"].isin(test).to_numpy()


def _model(params: dict, n_class: int, seed: int):
    from xgboost import XGBClassifier
    p = {k: v for k, v in params.items() if k != "class_weight"}
    return XGBClassifier(n_estimators=N_TREES, objective="multi:softprob", num_class=n_class, tree_method="hist",
                         random_state=seed, n_jobs=1, **p)


def _fit(params: dict, X, y, n_class: int, seed: int):
    w = compute_sample_weight("balanced", y) if params.get("class_weight") == "balanced" else None
    return _model(params, n_class, seed).fit(X, y, sample_weight=w)


@traced
def tune(X: pd.DataFrame, y: np.ndarray, groups: np.ndarray, n_class: int, seed: int = 0,
         grid: dict | None = None, folds: int = 5) -> dict:
    """Grid search by grouped k-fold (people never split across folds), scored by macro F1. A fold whose
    training part lacks a class is skipped (xgboost can't fit it); `cv_folds_used` says how many were left."""
    grid = grid or GRID
    keys = list(grid)
    cv = [(tr, va) for tr, va in GroupKFold(n_splits=folds).split(X, y, groups)
          if len(np.unique(y[tr])) == n_class]
    if not cv:
        raise ValueError(f"every training fold lacks a class: fewer people per class than folds ({folds})")
    best, best_score = None, -1.0
    for values in itertools.product(*(grid[k] for k in keys)):
        params = dict(zip(keys, values))
        scores = [f1_score(y[va], _fit(params, X.iloc[tr], y[tr], n_class, seed).predict(X.iloc[va]),
                           average="macro", labels=list(range(n_class)), zero_division=0) for tr, va in cv]
        if np.mean(scores) > best_score:
            best, best_score = params, float(np.mean(scores))
    return best | {"cv_macro_f1": best_score, "cv_folds_used": len(cv)}


@traced
def shap_values(model, X: pd.DataFrame) -> np.ndarray:
    """Exact TreeSHAP: (visits, classes, features + bias); each row adds up to the class margin."""
    from xgboost import DMatrix
    phi = model.get_booster().predict(DMatrix(X, missing=np.nan), pred_contribs=True)
    return np.asarray(phi).reshape(len(X), -1, X.shape[1] + 1)


@traced
def train_eval(f: pd.DataFrame, scheme: str, seed: int = 0, grid: dict | None = None, folds: int = 5) -> dict:
    names = CLASS_NAMES[scheme]
    n_class = len(names)
    te = split_people(f, seed)
    X, y = f[FEATURES], f["y"].to_numpy()
    missing = [names[k] for k in range(n_class) if not (y[~te] == k).any()]
    if missing:
        raise ValueError(f"no {', '.join(missing)} among the training people: the model can't learn it "
                         "(a larger study, or a coarser scheme such as 3level)")
    best = tune(X[~te], y[~te], f.loc[~te, "person_id"].to_numpy(), n_class, seed, grid, folds)
    params = {k: v for k, v in best.items() if k not in ("cv_macro_f1", "cv_folds_used")}
    model = _fit(params, X[~te], y[~te], n_class, seed)
    Xt, yt = X[te], y[te]
    proba = model.predict_proba(Xt)
    pred = proba.argmax(axis=1)

    rows = []
    for k, name in enumerate(names):
        pos, hit = yt == k, pred == k
        rows.append({"class": name, "n_test": int(pos.sum()),
                     "auroc": roc_auc_score(pos, proba[:, k]) if 0 < pos.sum() < len(pos) else np.nan,
                     "sensitivity": (hit & pos).sum() / pos.sum() if pos.any() else np.nan,
                     "specificity": (~hit & ~pos).sum() / (~pos).sum() if (~pos).any() else np.nan})
    metrics = pd.DataFrame(rows)

    phi = shap_values(model, Xt)
    imp = pd.DataFrame({"feature": FEATURES, "role": [AAP_ROLE[c] for c in FEATURES],
                        "mean_abs_shap": np.abs(phi[:, :, :-1]).mean(axis=(0, 1))})
    for k, name in enumerate(names):
        imp[f"mean_abs_shap_{name}"] = np.abs(phi[:, k, :-1]).mean(axis=0)
    imp = imp.sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)
    per = pd.concat([pd.DataFrame(phi[:, k, :], columns=[*FEATURES, "bias"])
                     .assign(visit_id=f.loc[te, "visit_id"].to_numpy(), **{"class": name})
                     for k, name in enumerate(names)], ignore_index=True)
    per = per[["visit_id", "class", *FEATURES, "bias"]]

    summary = {"scheme": scheme, "n_train": int((~te).sum()), "n_test": int(te.sum()),
               "people_test": int(f.loc[te, "person_id"].nunique()), "accuracy": float(accuracy_score(yt, pred)),
               "macro_f1": float(f1_score(yt, pred, average="macro", labels=list(range(n_class)), zero_division=0)),
               "cv_macro_f1": best["cv_macro_f1"], "cv_folds_used": best["cv_folds_used"], "params": params}
    return {"summary": summary, "metrics": metrics, "shap_importance": imp, "shap_test": per, "model": model,
            "X_test": Xt, "test_predictions": pd.DataFrame({"visit_id": f.loc[te, "visit_id"].to_numpy(),
                                                            "y": yt, "pred": pred})}
