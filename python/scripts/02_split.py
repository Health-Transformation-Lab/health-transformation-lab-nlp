"""Write data/labels/split.csv (patient-level, seed 42). Run once; every rung reuses it."""

import sys

import pandas as pd

from dental_omop_nlp.paths import LABELS_DIR, REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "eval"))
from split import make_split

notes = pd.read_parquet(LABELS_DIR / "labeled_notes.parquet")
split = make_split(notes)
split.to_csv(LABELS_DIR / "split.csv", index=False)
print(split["split"].value_counts().to_string())
