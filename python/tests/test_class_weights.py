"""Class-weighted fine-tuning for the rare stage IV class (spec 002 T016)."""

import pytest

from dental_omop_nlp.labels import LABELS
from dental_omop_nlp.registry import load_registry
from dental_omop_nlp.rungs import HFEncoder, class_weights, make_rung


def test_sqrt_inverse_frequency_weights_average_one():
    labels = ["healthy"] * 400 + ["periodontitis_stage_4"] * 4 + ["gingivitis"] * 100
    w = class_weights(labels, LABELS)
    seen = [w[LABELS.index(c)] for c in ("healthy", "gingivitis", "periodontitis_stage_4")]
    assert seen[2] > seen[1] > seen[0]
    assert seen[2] / seen[0] == pytest.approx((400 / 4) ** 0.5)       # square root of the frequency ratio
    assert sum(w[LABELS.index(c)] * n for c, n in [("healthy", 400), ("gingivitis", 100),
                                                    ("periodontitis_stage_4", 4)]) / 504 == pytest.approx(1.0)
    assert w[LABELS.index("periodontitis_stage_1")] == 0.0           # absent class: no weight


def test_make_rung_passes_class_weight_and_seed_and_keeps_runs_apart():
    reg = load_registry()
    a = make_rung("bert-base", reg, class_weight="sqrt", seed=7)
    b = make_rung("bert-base", reg)
    assert isinstance(a, HFEncoder) and a.class_weight == "sqrt" and a.seed == 7
    assert b.class_weight is None and b.seed == 42
    assert a.run_dir != b.run_dir                                    # checkpoints never collide


def test_registry_has_the_clinical_encoders():
    ids = {m["id"]: m for m in load_registry()["models"]}
    for i in ("bio-clinicalbert", "gatortron-base"):
        assert ids[i]["role"] == "classifier" and ids[i]["domain"] == "clinical"
