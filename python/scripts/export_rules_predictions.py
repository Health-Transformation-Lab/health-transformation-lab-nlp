"""Write the Python rules predictions and their score for r/tests/test_parity.R."""

import sys

import pandas as pd

from dental_omop_nlp.paths import LABELS_DIR, REPO_ROOT
from dental_omop_nlp.rungs import rules_predict

sys.path.insert(0, str(REPO_ROOT / "eval"))
from score import score

notes = pd.read_parquet(LABELS_DIR / "labeled_notes.parquet")
notes["pred"] = [rules_predict(t) for t in notes["note_text"]]
notes[["note_id", "pred"]].to_csv(LABELS_DIR / "python_rules_predictions.csv", index=False)

test = notes.merge(pd.read_csv(LABELS_DIR / "split.csv"), on="person_id").query("split == 'test'")
score(test["label"], test["pred"], None, "rules_baseline", run_id="parity").to_csv(
    LABELS_DIR / "python_rules_score.csv", index=False)
print("wrote python_rules_predictions.csv and python_rules_score.csv")
