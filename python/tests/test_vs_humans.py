"""AI vs human agreement benchmark (after OHDSI case-validation work: an AI rater is
acceptable if it agrees with the reviewers at least as much as they agree with each other)."""

import random

import numpy as np
import pandas as pd

from health_transformation_lab_nlp.labels import LABELS
from health_transformation_lab_nlp.reliability import _kappa_where_both, agreement_vs_humans


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


def _kappa_reference(a, b):
    # The original pandas implementation; the fast one must match it exactly.
    cats = sorted(set(a) | set(b))
    if len(a) == 0:
        return float("nan")
    po = (a.values == b.values).mean()
    pe = sum((a == c).mean() * (b == c).mean() for c in cats)
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def test_fast_kappa_matches_pandas_reference_exactly():
    from health_transformation_lab_nlp.reliability import VALID, _kappa_where_both
    from health_transformation_lab_nlp.phenotype import cohen_kappa
    rng = np.random.default_rng(3)
    for dtype, vals in ((object, np.array([*VALID, "unsure", None], dtype=object)),
                        ("str", np.array([*VALID, "unsure"], dtype=object))):
        for _ in range(50):
            n = int(rng.integers(0, 40))
            idx = rng.permutation(n)   # callers pass two series on the same index
            a = pd.Series(rng.choice(vals, n), dtype=dtype, index=idx)
            b = pd.Series(rng.choice(vals, n), dtype=dtype, index=idx)
            ok = a.isin(VALID).values & b.isin(VALID).values
            ref = _kappa_reference(a[ok], b[ok])
            got = _kappa_where_both(a, b)
            assert (np.isnan(ref) and np.isnan(got)) or ref == got
            fa, fb = a.dropna(), b.dropna().iloc[:len(a.dropna())]
            fa = fa.iloc[:len(fb)]
            r2, g2 = _kappa_reference(fa, fb), cohen_kappa(fa, fb)
            assert (np.isnan(r2) and np.isnan(g2)) or r2 == g2


def test_kappa_on_label_codes_equals_kappa_on_labels_exactly():
    """The bootstrap runs kappa ~40,000 times on integer codes; it must give the very same floats."""
    from health_transformation_lab_nlp.reliability import _kappa_codes, _label_codes
    rng = random.Random(3)
    pool = [*LABELS, "healthy_gingivitis", "unknown", None, float("nan")]
    for _ in range(300):
        n = rng.randint(0, 60)
        a = pd.Series([rng.choice(pool) for _ in range(n)], dtype=object)
        b = pd.Series([rng.choice(pool) for _ in range(n)], dtype=object)
        want, got = _kappa_where_both(a, b), _kappa_codes(_label_codes(a), _label_codes(b))
        assert (np.isnan(want) and np.isnan(got)) or want == got
