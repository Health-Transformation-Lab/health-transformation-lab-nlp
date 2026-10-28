"""Load models.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

from .paths import MODELS_YAML
from .telemetry import traced


@traced
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


@traced
def families_of(reg: dict, methods) -> set[str]:
    """Model families of the evaluated methods (ids may carry sim:/ai: prefixes).
    Used so an LLM judge never grades its own family."""
    by_id = {m["id"]: m.get("family") for m in reg["models"]}
    out = set()
    for meth in methods:
        mid = meth.split(":", 1)[-1]
        if by_id.get(mid):
            out.add(by_id[mid])
    return out


@traced
def model(reg: dict, model_id: str) -> dict:
    for m in reg["models"]:
        if m["id"] == model_id:
            return m
    raise KeyError(model_id)
