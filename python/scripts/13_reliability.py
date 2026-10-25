"""Quantitative validation: reviewers vs each other, and every method, the
rule-based algorithm and each AI model vs the reviewers.

    python scripts/13_reliability.py              # uses reviewer_labels.csv
    python scripts/13_reliability.py --simulated  # uses simulated_reviewer_labels.csv (dry run)
"""

import argparse
import glob
from pathlib import Path

import pandas as pd

from dental_omop_nlp.paths import DATASETS_DIR, REVIEW_DIR
from dental_omop_nlp.reliability import reliability_report

ap = argparse.ArgumentParser()
ap.add_argument("--simulated", action="store_true")
a = ap.parse_args()
prefix = "simulated_" if a.simulated else ""

labels = pd.read_csv(REVIEW_DIR / f"{prefix}reviewer_labels.csv")
key = pd.read_csv(DATASETS_DIR / "answer_key" / "review_key.csv").set_index("visit_id")
compare = {m: key[m] for m in ["notes", "exam_form", "proc_codes_completed", "proc_codes_planned",
                               "proc_dx_completed", "proc_dx_planned", "probing_chart", "algorithm_v0"]}
for f in sorted(glob.glob(str(DATASETS_DIR / "ai_predictions_*.csv"))):
    p = pd.read_csv(f).set_index("visit_id")["pred"]
    compare["ai:" + Path(f).stem.removeprefix("ai_predictions_")] = p
rep = reliability_report(labels, key, compare)

out = REVIEW_DIR / f"{prefix}reliability"
out.mkdir(parents=True, exist_ok=True)
rep["pairwise"].to_csv(out / "reviewer_pairwise.csv", index=False)
rep["methods"].to_csv(out / "methods_vs_reviewers.csv", index=False)
rep["consensus"].to_csv(out / "consensus.csv")
if a.simulated:
    print("*** SIMULATED REVIEWERS: pipeline dry run, not a result ***")
print(f"charts={rep['n_visits']} reviewers={rep['n_reviewers']} "
      f"Fleiss kappa={rep['fleiss_kappa']:.3f} consensus reached={rep['consensus_reached']:.1%}")
print(rep["methods"].round(3).to_string(index=False))
