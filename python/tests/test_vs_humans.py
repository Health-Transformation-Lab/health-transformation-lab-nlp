"""AI vs human agreement benchmark (after OHDSI case-validation work: an AI rater is
acceptable if it agrees with the reviewers at least as much as they agree with each other)."""

import random

import numpy as np
import pandas as pd

from dental_omop_nlp.labels import LABELS
from dental_omop_nlp.reliability import _kappa_where_both, agreement_vs_humans


def _panel(n=200, n_rev=4, err=0.15, seed=0):
    rng = random.Random(seed)
    truth = [rng.choice(LABELS) for _ in range(n)]
    noisy = lambda t, e: t if rng.random() > e else rng.choice(LABELS)
    wide = pd.DataFrame({f"r{i}": [noisy(t, err) for t in truth] for i in range(n_rev)},
                        index=pd.Index(range(1, n + 1), name="visit_id"))
    return wide, pd.Series(truth, index=wide.index), noisy


def test_human_bar_and_rows():
    wide, truth, _ = _panel()
    t = agreement_vs_humans(wide, {"good": truth}, n_boot=50)
    humans = t[t["kind"] == "human"]
    assert len(humans) == 4
    pairs = [_kappa_where_both(wide[a], wide[b]) for a in wide for b in wide if a < b]
    bar = t.loc[t["rater"] == "humans (mean pairwise)", "mean_kappa_vs_humans"].item()
    assert np.isclose(bar, np.mean(pairs))
    g = t[t["rater"] == "good"].iloc[0]
    assert np.isclose(g["diff_vs_human_bar"], g["mean_kappa_vs_humans"] - bar)


def test_verdicts():
    wide, truth, _ = _panel(n=300)
    rng = random.Random(9)
    bad = pd.Series([rng.choice(LABELS) for _ in truth], index=truth.index)
    t = agreement_vs_humans(wide, {"truth_like": truth, "random": bad}, n_boot=200, margin=0.05).set_index("rater")
    assert t.loc["truth_like", "verdict"] == "non-inferior"
    assert t.loc["random", "verdict"] == "inferior"
    assert t.loc["truth_like", "ci_low"] <= t.loc["truth_like", "diff_vs_human_bar"] <= t.loc["truth_like", "ci_high"]


def test_seeded():
    wide, truth, _ = _panel()
    a = agreement_vs_humans(wide, {"m": truth}, n_boot=30, seed=3)
    b = agreement_vs_humans(wide, {"m": truth}, n_boot=30, seed=3)
    pd.testing.assert_frame_equal(a, b)
