"""docs/model_inventory.md lists every model and AI service the code can use (for an AI-use review)."""

import re

import yaml

from dental_omop_nlp.paths import REPO_ROOT

DOC = (REPO_ROOT / "docs" / "model_inventory.md").read_text()


def test_every_registry_model_is_listed():
    models = yaml.safe_load((REPO_ROOT / "models.yaml").read_text())["models"]
    missing = [m["hf"] for m in models if f"`{m['hf']}`" not in DOC]
    assert not missing, f"add to docs/model_inventory.md: {missing}"


def test_models_and_services_named_in_code_are_listed():
    code = "".join(p.read_text() for p in (REPO_ROOT / "python").rglob("*.py") if "tests" not in p.parts)
    code += (REPO_ROOT / "databricks.yml").read_text()
    hf_ids = set(re.findall(r'"((?:obi|StanfordAIMI|allenai|google|UFNLP|microsoft)/[A-Za-z0-9_.-]+)"', code))
    endpoints = set(re.findall(r"databricks-[a-z0-9-]+-instruct", code))
    for name in sorted(hf_ids | endpoints | {"en_core_web_lg", "ai_mask"}):
        assert name in DOC, f"{name} is used in code but missing from docs/model_inventory.md"


def test_licence_gaps_are_called_out():
    assert DOC.count("none on the card") >= 2 and "HAI-DEF" in DOC
