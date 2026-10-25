"""Load models.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

from .paths import MODELS_YAML


def load_registry(path: Path | str = MODELS_YAML) -> dict:
    with open(path) as f:
        reg = yaml.safe_load(f)
    ids = {m["id"] for m in reg["models"]}
    builtins = {"rules_baseline", "note_rules", "structured_baseline", "tfidf_logreg", "fusion_tfidf_rad",
                "llm_challenger"}
    for ladder, rungs in reg["ladders"].items():
        unknown = [r for r in rungs if r not in ids | builtins]
        if unknown:
            raise ValueError(f"ladder {ladder!r} references unknown models: {unknown}")
    return reg


def model(reg: dict, model_id: str) -> dict:
    for m in reg["models"]:
        if m["id"] == model_id:
            return m
    raise KeyError(model_id)
