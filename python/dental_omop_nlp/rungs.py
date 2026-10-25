"""The model ladder. Each rung: fit(train_df) -> predict(test_df) -> (labels, proba|None).

note_rules           rules for clinical notes (note_reader.py): stated dx, else findings.
rules_baseline       regex for the short templated notes + the staging rules in labels.py.
                     On synthetic notes this is a strong baseline because the numbers
                     are usually in the text; that is a property of synthetic data and
                     the reason real notes are the real test.
structured_baseline  logistic regression on the chart numerics (not the text). Upper
                     bound for "what the chart knows".
tfidf_logreg         TF-IDF + logistic regression on the text. Cheapest text model.
<hf id>              any `classifier` / `long_context` model in models.yaml, fine-tuned
                     with a sequence-classification head via transformers.Trainer.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from .labels import LABELS, PerioChart, label_chart

CHART_COLS = ["max_probing_depth_mm", "bop_pct", "max_cal_mm", "rbl_pct", "teeth_lost_perio"]


# ---------------------------------------------------------------- rules
_NUM = r"(\d+(?:\.\d+)?)"
_PATTERNS = {
    "pd": [rf"PD max {_NUM}", rf"probing depths up to {_NUM}", rf"deepest pocket {_NUM}"],
    "bop": [rf"BOP {_NUM}%", rf"bleeding at {_NUM}%"],
    "cal": [rf"CAL {_NUM}", rf"attachment loss {_NUM}"],
    "rbl": [rf"RBL ~?{_NUM}%", rf"{_NUM}% horizontal bone loss"],
    "lost": [rf"{_NUM} teeth previously lost"],
}
_NEG_BOP = re.compile(r"no BOP|BOP neg|no bleeding on probing", re.IGNORECASE)


def _find(text: str, key: str) -> float | None:
    for p in _PATTERNS[key]:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return float(m.group(1))
    return None


def rules_predict(text: str) -> str:
    bop = 0.0 if _NEG_BOP.search(text) else (_find(text, "bop") or 0.0)
    chart = PerioChart(max_probing_depth_mm=_find(text, "pd") or 0.0, bop_pct=min(bop, 100),
                       max_cal_mm=_find(text, "cal") or 0.0, rbl_pct=min(_find(text, "rbl") or 0.0, 100),
                       teeth_lost_perio=int(_find(text, "lost") or 0))
    return label_chart(chart).value


class NoteRules:
    """Rules for clinical notes: stated diagnosis in any scheme, else findings (note_reader.py)."""

    def fit(self, train: pd.DataFrame):
        return self

    def predict(self, test: pd.DataFrame):
        from .note_reader import read_note
        return [read_note(t) for t in test["note_text"]], None


class RulesBaseline:
    def fit(self, train: pd.DataFrame):
        return self

    def predict(self, test: pd.DataFrame):
        return [rules_predict(t) for t in test["note_text"]], None


# ---------------------------------------------------------------- sklearn
class _SkWrap:
    def __init__(self, est, cols: str | list[str]):
        self.est, self.cols = est, cols

    def fit(self, train):
        self.est.fit(train[self.cols], train["label"])
        return self

    def predict(self, test):
        proba = self.est.predict_proba(test[self.cols])
        cls = list(self.est.classes_)
        full = np.zeros((len(test), len(LABELS)))  # align to LABEL order; absent classes stay 0
        for j, lab in enumerate(cls):
            full[:, LABELS.index(lab)] = proba[:, j]
        return [LABELS[i] for i in full.argmax(axis=1)], full


def structured_baseline():
    return _SkWrap(LogisticRegression(max_iter=2000), CHART_COLS)


def tfidf_logreg():
    return _SkWrap(make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2),
                                 LogisticRegression(max_iter=2000)), "note_text")


# ---------------------------------------------------------------- transformers
class HFEncoder:
    """Fine-tune a Hugging Face encoder. CPU works for the small models on a few
    hundred notes; set epochs/max_len down on Databricks Free Edition."""

    def __init__(self, hf_id: str, max_len: int = 256, epochs: int = 3, batch_size: int = 16,
                 lr: float = 5e-5, out_dir: str = "runs"):
        self.hf_id, self.max_len, self.epochs = hf_id, max_len, epochs
        self.batch_size, self.lr, self.out_dir = batch_size, lr, out_dir

    def _ds(self, df):
        from datasets import Dataset
        d = Dataset.from_pandas(df[["note_text"]].assign(
            labels=[LABELS.index(x) for x in df["label"]] if "label" in df else 0))
        return d.map(lambda b: self.tok(b["note_text"], truncation=True, max_length=self.max_len,
                                        padding="max_length"), batched=True)

    def fit(self, train):
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            Trainer,
            TrainingArguments,
        )
        self.tok = AutoTokenizer.from_pretrained(self.hf_id)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.hf_id, num_labels=len(LABELS), id2label=dict(enumerate(LABELS)),
            label2id={l: i for i, l in enumerate(LABELS)}, ignore_mismatched_sizes=True)
        args = TrainingArguments(output_dir=f"{self.out_dir}/{self.hf_id.replace('/', '__')}",
                                 num_train_epochs=self.epochs, per_device_train_batch_size=self.batch_size,
                                 learning_rate=self.lr, logging_steps=20, save_strategy="no",
                                 report_to=[], seed=42)
        self.trainer = Trainer(model=self.model, args=args, train_dataset=self._ds(train))
        self.trainer.train()
        return self

    def predict(self, test):
        import torch
        logits = self.trainer.predict(self._ds(test)).predictions
        proba = torch.softmax(torch.tensor(logits), dim=-1).numpy()
        return [LABELS[i] for i in proba.argmax(axis=1)], proba


def make_rung(rung_id: str, registry: dict, **hf_kwargs):
    if rung_id == "rules_baseline":
        return RulesBaseline()
    if rung_id == "note_rules":
        return NoteRules()
    if rung_id == "structured_baseline":
        return structured_baseline()
    if rung_id == "tfidf_logreg":
        return tfidf_logreg()
    if rung_id == "llm_challenger":
        raise NotImplementedError("LLM rung runs on Databricks Model Serving; see databricks/notebooks")
    m = next((m for m in registry["models"] if m["id"] == rung_id), None)
    if m is None:
        raise KeyError(f"unknown rung {rung_id!r}")
    if m["role"] not in ("classifier", "long_context"):
        raise ValueError(f"{rung_id} has role {m['role']!r}; it is not a classifier rung")
    hf_kwargs.setdefault("max_len", min(m["max_len"], 256))
    return HFEncoder(m["hf"], **hf_kwargs)
