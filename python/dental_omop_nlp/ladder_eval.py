"""The model ladder against the synthetic truth (spec 002 T015).

The review charts' true status is known (the generator wrote it), so each method's accuracy can be
measured directly, not only as agreement with reviewers. Per method:

  accuracy            share of charts labelled correctly, with a 95% bootstrap CI
  diff_vs_ref         accuracy minus the reference method's (note_rules), paired bootstrap CI:
                      the same resampled charts for both, so the CI reflects the difference itself
  stage4_recall       share of stage IV charts called stage IV
  unsafe_rate/s2_rate harm.py's severity matrix against the truth
  ece                 expected calibration error of the top-class probability (10 bins)

`rules_override` is the stage IV hybrid: where the note rules say stage IV, use that; otherwise the
model. Fine-tuned encoders saw 7 stage IV notes in training and miss nearly all of them.
R twin: r/R/10_ladder.R (point estimates; bootstrap CIs differ by RNG).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .harm import unsafe_rates

STAGE4 = "periodontitis_stage_4"


def rules_override(pred: pd.Series, rules_pred: pd.Series, labels=(STAGE4,)) -> pd.Series:
    return rules_pred.where(rules_pred.isin(labels), pred)


def expected_calibration_error(truth: pd.Series, proba: pd.DataFrame, n_bins: int = 10) -> float:
    conf = proba.max(axis=1).to_numpy()
    correct = (proba.idxmax(axis=1).to_numpy() == truth.to_numpy())
    bins = np.minimum((conf * n_bins).astype(int), n_bins - 1)
    return float(sum(abs(conf[bins == b].mean() - correct[bins == b].mean()) * (bins == b).mean()
                     for b in range(n_bins) if (bins == b).any()))


def ladder_table(truth: pd.Series, preds: dict, proba: dict | None = None, n_boot: int = 1000,
                 seed: int = 0, reference: str = "note_rules") -> pd.DataFrame:
    """One row per method. All series share truth's index (one row per chart)."""
    proba = proba or {}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(truth), size=(n_boot, len(truth)))   # same resamples for every method
    t = truth.to_numpy()
    correct = {m: (p.reindex(truth.index).to_numpy() == t) for m, p in preds.items()}
    ref = correct.get(reference)
    s4 = t == STAGE4
    rows = []
    for m, p in preds.items():
        c = correct[m]
        boot = c[idx].mean(axis=1)
        row = {"method": m, "n": len(t), "accuracy": c.mean(),
               "acc_lo": np.quantile(boot, 0.025), "acc_hi": np.quantile(boot, 0.975),
               "stage4_recall": c[s4].mean() if s4.any() else np.nan,
               **{k: v for k, v in unsafe_rates(truth, p.reindex(truth.index)).items() if k != "n"},
               "ece": expected_calibration_error(truth, proba[m].reindex(truth.index)) if m in proba else np.nan}
        if ref is not None:
            d = (c[idx].mean(axis=1) - ref[idx].mean(axis=1))
            row |= {"diff_vs_ref": c.mean() - ref.mean(), "diff_lo": np.quantile(d, 0.025),
                    "diff_hi": np.quantile(d, 0.975)}
        rows.append(row)
    return pd.DataFrame(rows)
