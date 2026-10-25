"""Train an AI rung on the training set and predict the chart-review notes.

The AI model reads ONLY the de-identified note. Reviewers see every source.

    python scripts/11_ai_predict.py --rung tfidf_logreg
    python scripts/11_ai_predict.py --rung distilbert-base --epochs 2 --max-len 256
    python scripts/11_ai_predict.py --rung bioclinical-modernbert-base --label stated_status

Writes data/datasets/ai_predictions_<rung>.csv (visit_id, pred, p_<status>...).
"""

import argparse

import pandas as pd

from dental_omop_nlp.labels import LABELS
from dental_omop_nlp.paths import DATASETS_DIR
from dental_omop_nlp.registry import load_registry
from dental_omop_nlp.rungs import make_rung

ap = argparse.ArgumentParser()
ap.add_argument("--rung", required=True)
ap.add_argument("--label", default="label", help="train target: label (chart) or stated_status (clinician)")
ap.add_argument("--epochs", type=int, default=3)
ap.add_argument("--max-len", type=int, default=256)
a = ap.parse_args()

train = pd.read_csv(DATASETS_DIR / "train.csv").rename(columns={a.label: "target"})
train = train.drop(columns=[c for c in ("label",) if c in train]).rename(columns={"target": "label"})
from dental_omop_nlp.radiograph import FEATURES as RAD_FEATURES  # noqa: E402

review = pd.read_csv(DATASETS_DIR / "answer_key" / "review_key.csv")[["visit_id", "note_text", *RAD_FEATURES]]
kw = {} if a.rung in ("rules_baseline", "note_rules", "tfidf_logreg", "fusion_tfidf_rad") else {"epochs": a.epochs, "max_len": a.max_len}
model = make_rung(a.rung, load_registry(), **kw).fit(train)
pred, proba = model.predict(review)
out = review[["visit_id"]].assign(pred=pred)
if proba is not None:
    for i, lab in enumerate(LABELS):
        out[f"p_{lab}"] = proba[:, i]
path = DATASETS_DIR / f"ai_predictions_{a.rung}.csv"
out.to_csv(path, index=False)
print(f"wrote {path} ({len(out)} visits)")
