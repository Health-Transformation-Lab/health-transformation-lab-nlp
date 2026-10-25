"""Shared scorer (Python). eval/score.R is the R twin; both write the same schema."""

from __future__ import annotations

import datetime as dt
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, roc_auc_score

LABEL_ORDER = ["healthy", "gingivitis", "periodontitis_stage_1",
               "periodontitis_stage_2", "periodontitis_stage_3", "periodontitis_stage_4"]
PERIO = set(LABEL_ORDER[2:])


def score(y_true, y_pred, proba: np.ndarray | None, model_id: str,
          language: str = "python", run_id: str | None = None) -> pd.DataFrame:
    """proba: (n, 6) in LABEL_ORDER, or None."""
    y_true, y_pred = list(y_true), list(y_pred)
    run_id = run_id or f"{model_id}-{uuid.uuid4().hex[:8]}"
    ts = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    rows = []

    def add(metric, value, cls=""):
        rows.append(dict(run_id=run_id, model_id=model_id, language=language, metric=metric,
                         **{"class": cls}, value=None if value is None else float(value),
                         n_test=len(y_true), timestamp=ts))

    add("macro_f1", f1_score(y_true, y_pred, labels=LABEL_ORDER, average="macro", zero_division=0))
    for lab, f in zip(LABEL_ORDER, f1_score(y_true, y_pred, labels=LABEL_ORDER,
                                            average=None, zero_division=0)):
        add("f1", f, lab)

    t = np.array([y in PERIO for y in y_true])
    p = np.array([y in PERIO for y in y_pred])
    tp, fn = int((t & p).sum()), int((t & ~p).sum())
    tn, fp = int((~t & ~p).sum()), int((~t & p).sum())
    add("sensitivity", tp / (tp + fn) if tp + fn else None)
    add("specificity", tn / (tn + fp) if tn + fp else None)

    auroc = None
    if proba is not None and t.any() and (~t).any():
        auroc = roc_auc_score(t, np.asarray(proba)[:, 2:].sum(axis=1))
    add("auroc", auroc)
    return pd.DataFrame(rows)


def write(results: pd.DataFrame, results_dir: Path) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    out = results_dir / f"{results['run_id'].iloc[0]}.csv"
    results.to_csv(out, index=False)
    return out
