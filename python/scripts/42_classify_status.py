"""Classify periodontal status from the recorded chart and explain it with SHAP (spec 013 G10).

    python scripts/42_classify_status.py [--outcome algorithm_design|truth_status] [--scheme 5level|3level]

Gradient-boosted trees (XGBoost, the `ml` extra), people split 80/20, hyperparameters by 5-fold grouped
cross-validation, one-vs-rest metrics, exact TreeSHAP on the held-out visits. SYNTHETIC: the labels come from
the AAP rules on the same chart, so the SHAP ranking checks the pipeline; it says nothing about real patients.
Writes data/datasets/classify_status/<outcome>_<scheme>_*.csv and a SHAP summary figure.
"""

import argparse
import json

import numpy as np
import pandas as pd

from health_transformation_lab_nlp import classify_status as cs
from health_transformation_lab_nlp.paths import DATASETS_DIR

ap = argparse.ArgumentParser()
ap.add_argument("--outcome", default="algorithm_design", choices=["algorithm_design", "truth_status"])
ap.add_argument("--scheme", default="5level", choices=sorted(cs.SCHEMES))
ap.add_argument("--seed", type=int, default=3)
a = ap.parse_args()

v = pd.read_csv(DATASETS_DIR / "visits_structured.csv")
if a.outcome == "truth_status":
    v = v.merge(pd.read_csv(DATASETS_DIR / "answer_key" / "visits_truth.csv")[["visit_id", "truth_status"]],
                on="visit_id")
f = cs.features(v, a.outcome, a.scheme)
res = cs.train_eval(f, a.scheme, seed=a.seed)
out = DATASETS_DIR / "classify_status"
out.mkdir(exist_ok=True)
stem = f"{a.outcome}_{a.scheme}"
summary = res["summary"] | {"outcome": a.outcome, "params": json.dumps(res["summary"]["params"]), "synthetic": True}
pd.DataFrame([summary]).to_csv(out / f"{stem}_summary.csv", index=False)
res["metrics"].to_csv(out / f"{stem}_metrics.csv", index=False)
res["shap_importance"].to_csv(out / f"{stem}_shap_importance.csv", index=False)
res["shap_test"].round(5).to_csv(out / f"{stem}_shap_test.csv", index=False)
res["test_predictions"].to_csv(out / f"{stem}_test_predictions.csv", index=False)

# ---- SHAP summary: mean |SHAP| per class (left), beeswarm for the most severe class (right)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

names = cs.CLASS_NAMES[a.scheme]
imp = res["shap_importance"].iloc[::-1]                       # largest at the top
fig, (left, right) = plt.subplots(1, 2, figsize=(14, 6))
base = np.zeros(len(imp))
for name, color in zip(names, plt.cm.viridis(np.linspace(0.1, 0.9, len(names)))):
    vals = imp[f"mean_abs_shap_{name}"].to_numpy() / len(names)
    left.barh(imp["feature"], vals, left=base, color=color, label=name)
    base += vals
left.set_yticks(range(len(imp)), [f"{r.feature}  [{r.role}]" for r in imp.itertuples()])
left.set_xlabel("mean |SHAP| (log-odds), stacked by class")
left.legend(fontsize=8, loc="lower right")
sev = names[-1]
per = res["shap_test"][res["shap_test"]["class"] == sev]
X = res["X_test"]
rng = np.random.default_rng(0)
for i, feat in enumerate(imp["feature"]):
    x = X[feat].to_numpy(dtype=float)
    lo, hi = np.nanmin(x), np.nanmax(x)
    color = (x - lo) / (hi - lo) if hi > lo else np.zeros_like(x)
    right.scatter(per[feat], i + rng.uniform(-0.3, 0.3, len(per)), c=np.nan_to_num(color, nan=0.5), cmap="coolwarm",
                  s=6, alpha=0.7)
right.set_yticks(range(len(imp)), imp["feature"])
right.axvline(0, color="grey", lw=0.8)
right.set_xlabel(f"SHAP value for {sev} (log-odds; red = high feature value)")
fig.suptitle(f"What drives the status model ({a.scheme}, outcome {a.outcome}); SYNTHETIC data")
fig.tight_layout()
fig.savefig(out / f"{stem}_shap.png", dpi=130)

s = res["summary"]
print(f"SYNTHETIC: {a.scheme} status from the recorded chart, outcome {a.outcome}")
print(f"train {s['n_train']} visits, test {s['n_test']} ({s['people_test']} people); best {s['params']} "
      f"(CV macro F1 {s['cv_macro_f1']:.3f})")
print(f"held out: accuracy {s['accuracy']:.3f}, macro F1 {s['macro_f1']:.3f}")
print(res["metrics"].round(3).to_string(index=False))
print(res["shap_importance"][["feature", "role", "mean_abs_shap"]].round(3).to_string(index=False))

from health_transformation_lab_nlp.tracking import track

with track("42_classify_status", stem, simulated=True, params=s["params"] | {"scheme": a.scheme}) as run:
    run.log_metrics({k: s[k] for k in ("accuracy", "macro_f1", "cv_macro_f1")})
    run.log_artifact(out / f"{stem}_shap_importance.csv")
