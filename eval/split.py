"""Make the one patient-level split every rung uses. See eval/README.md."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

LABEL_ORDER = ["healthy", "gingivitis", "periodontitis_stage_1",
               "periodontitis_stage_2", "periodontitis_stage_3", "periodontitis_stage_4"]


def make_split(notes: pd.DataFrame, test_size: float = 0.2, seed: int = 42) -> pd.DataFrame:
    rank = {lab: i for i, lab in enumerate(LABEL_ORDER)}
    worst = (notes.assign(r=notes["label"].map(rank))
             .groupby("person_id")["r"].max().rename("worst").reset_index())
    # Stratify only if every stratum has at least 2 people; tiny samples can't.
    strat = worst["worst"] if worst["worst"].value_counts().min() >= 2 else None
    train_ids, test_ids = train_test_split(worst["person_id"], test_size=test_size,
                                           random_state=seed, stratify=strat)
    return pd.concat([pd.DataFrame({"person_id": train_ids, "split": "train"}),
                      pd.DataFrame({"person_id": test_ids, "split": "test"})]).sort_values("person_id")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("labels_dir", type=Path)
    a = ap.parse_args()
    notes = pd.read_parquet(a.labels_dir / "labeled_notes.parquet")
    split = make_split(notes)
    split.to_csv(a.labels_dir / "split.csv", index=False)
    print(split["split"].value_counts().to_string())
