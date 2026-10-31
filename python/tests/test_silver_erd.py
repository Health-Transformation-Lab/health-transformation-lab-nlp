"""Spec 029 US4 (#379): the Open Dental silver ERD and its OMOP alternative, drawn from declarations in
diagrams/_build/ the way the gold ERDs are."""
import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "diagrams" / "_build"
sys.path.insert(0, str(BUILD))       # the models import gold_model's dataclasses, as gold_erd does


def _load(name):
    spec = importlib.util.spec_from_file_location(name, BUILD / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


OD = _load("opendental_silver_model")
OM = _load("omop_silver_model")
RESEARCH = (ROOT / "specs" / "029-tooth-loss" / "research.md").read_text()


def _research_columns(table):
    """The columns research.md lists for an Open Dental table, lowercased."""
    section = RESEARCH.split(f"### `{table}`", 1)[1].split("\n### ", 1)[0].split("\n## ", 1)[0]
    cols = set()
    for line in section.splitlines():
        if line.startswith("| `"):
            cols |= {c.lower() for c in re.findall(r"`(\w+)`", line.split("|")[1])}
    return cols


def test_open_dental_tables_are_the_ones_spec_029_researched():
    source = [n for n, t in OD.TABLES.items() if t.area == "source"]
    assert set(source) == {"patient", "clinic", "procedurelog", "procedurecode", "treatplan", "proctp", "definition",
                           "perioexam", "periomeasure", "toothinitial", "disease", "diseasedef"}
    for name in source:
        allowed = _research_columns(name)
        for c in OD.TABLES[name].columns:
            assert c.name in allowed, f"{name}.{c.name} isn't in research.md's {name} table"
            assert c.name == c.name.lower()


def test_the_derived_tables_follow_spec_029():
    assert {"patient_tooth", "planned_extraction", "tooth_loss_dq_check", "tooth_loss_truth"} <= set(OD.TABLES)
    assert OD.TABLES["tooth_loss_truth"].area == "eval"


@pytest.mark.parametrize("model", [OD, OM], ids=["opendental", "omop"])
def test_every_relationship_joins_declared_columns(model):
    for r in model.RELATIONSHIPS:
        assert r.parent in model.TABLES and r.child in model.TABLES, r
        for t, cols in ((r.parent, r.parent_cols), (r.child, r.child_cols)):
            names = {c.name for c in model.TABLES[t].columns}
            assert set(cols) <= names, (t, cols)


@pytest.mark.parametrize("model", [OD, OM], ids=["opendental", "omop"])
def test_every_table_and_column_says_what_it_is(model):
    for name, t in model.TABLES.items():
        assert t.description and t.area in model.AREAS, name
        assert t.columns, name
        for c in t.columns:
            assert c.description, (name, c.name)


def test_the_plan_copies_quirk_is_drawn():
    rel = {(r.parent, r.child): r for r in OD.RELATIONSHIPS}
    assert ("procedurelog", "proctp") in rel and rel[("procedurelog", "proctp")].child_cols == ("procnumorig",)
    assert rel[("definition", "procedurelog")].child_cols == ("dx",) and not rel[("definition", "procedurelog")].derived
    assert rel[("definition", "proctp")].derived            # proctp.dx is text, matched by name, not a key


def test_every_omop_column_names_its_open_dental_source():
    for name, t in OM.TABLES.items():
        if t.area in ("cdm", "dental"):
            for c in t.columns:
                assert "←" in c.description or "not from Open Dental" in c.description, (name, c.name)
    assert "not_mapped" in OM.TABLES                            # what the CDM can't hold


def test_the_generated_files_are_current():
    erd = _load("silver_erd")
    for prefix, model in erd.MODELS:
        for stem, full in ((f"{prefix}_entity", False), (f"{prefix}_full", True)):
            assert (erd.SRC / f"{stem}.mmd").read_text() == erd.gold_erd.mermaid(full, model), \
                f"run python3 diagrams/_build/silver_erd.py ({stem}.mmd is stale)"
            assert (erd.SRC / f"{stem}.drawio").exists()
    assert (erd.OUT / "data_model.md").read_text() == erd.markdown()
