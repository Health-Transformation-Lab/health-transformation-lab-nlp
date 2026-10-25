"""Predict progression at the next visit from the current one (spec 005, US5).

    python scripts/21_predict_progression.py [--outcome algorithm_design|truth_status]

The outcome uses the integrated phenotype by default (what a real study would
have). Synthetic data: the important features are the ones the generator uses,
so this exercises the pipeline rather than finding anything. Writes
data/datasets/prediction/.
"""

import argparse

import pandas as pd

from dental_omop_nlp.paths import DATASETS_DIR
from dental_omop_nlp.prediction import make_pairs, train_eval

ap = argparse.ArgumentParser()
ap.add_argument("--outcome", default="algorithm_design")
ap.add_argument("--seed", type=int, default=3)
a = ap.parse_args()

v = pd.read_csv(DATASETS_DIR / "visits_structured.csv")
if a.outcome == "truth_status":
    v = v.merge(pd.read_csv(DATASETS_DIR / "answer_key" / "visits_truth.csv")[["visit_id", "truth_status"]],
                on="visit_id")
pairs = make_pairs(v, a.outcome)
res = train_eval(pairs, seed=a.seed)
out = DATASETS_DIR / "prediction"
out.mkdir(exist_ok=True)
res["importance"].to_csv(out / f"importance_{a.outcome}.csv", index=False)
summary = {k: v for k, v in res.items() if k != "importance"} | {"outcome": a.outcome}
pd.DataFrame([summary]).to_csv(out / f"summary_{a.outcome}.csv", index=False)

print(f"SYNTHETIC: outcome = progression of {a.outcome} at the next visit")
print(f"pairs train {res['n_pairs_train']}, test {res['n_pairs_test']}; progression rate {res['progress_rate']:.1%}")
print(f"AUROC {res['auroc']:.3f} (95% CI {res['auroc_ci_low']:.3f}-{res['auroc_ci_high']:.3f})")
print(res["importance"].round(4).to_string(index=False))
