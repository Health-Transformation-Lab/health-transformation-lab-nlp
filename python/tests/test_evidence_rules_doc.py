"""docs/evidence_rules.md: how each evidence type is turned into a status. Every worked example in the
doc is run through the code that reads that evidence type, so the doc can't drift from the code."""

import re

import pytest

from dental_omop_nlp import readme_results as rr
from dental_omop_nlp.labels import PerioChart, label_chart
from dental_omop_nlp.note_reader import read_note
from dental_omop_nlp.paths import REPO_ROOT
from dental_omop_nlp.radiograph import read_radiograph
from dental_omop_nlp.sources import read_exam_form, read_proc_codes, read_proc_dx

DOC = REPO_ROOT / "docs" / "evidence_rules.md"
EVIDENCE = ["probing_chart", "notes", "exam_form", "proc_dx_completed", "proc_dx_planned",
            "proc_codes_completed", "proc_codes_planned", "radiograph_ai"]


def _probing(s: str) -> str:
    n = {k: float(v) for k, v in re.findall(r"(CAL|PD|BOP|lost) (\d+(?:\.\d+)?)", s)}
    return label_chart(PerioChart(n.get("PD", 0), n.get("BOP", 0), n.get("CAL"), None, int(n.get("lost", 0)))).value


def _xray(s: str) -> str:
    m = re.match(r"max bone loss (\d+)%, (\d+) (?:teeth|tooth)", s)
    return read_radiograph({"present": True, "quality": "ok", "max_rbl_pct": float(m.group(1)),
                            "n_teeth_rbl15": int(m.group(2))})


READ = {"Gum measurements": _probing, "Chart note": read_note, "Exam form": read_exam_form,
        "Diagnosis codes": read_proc_dx, "Procedure codes": read_proc_codes, "X-ray AI": _xray}


def _examples():
    rows = []
    for line in DOC.read_text().splitlines():
        m = re.match(r"^\| (Gum measurements|Chart note|Exam form|Diagnosis codes|Procedure codes|X-ray AI) \| `([^`]*)` \| `([a-z0-9_]+)` \|", line)
        if m:
            rows.append(m.groups())
    return rows


def test_doc_has_a_section_for_every_evidence_type_by_its_readme_name():
    text = DOC.read_text()
    for e in EVIDENCE:
        name = "Chart note" if e == "notes" else rr._PLAIN[e]
        assert re.search(rf"^##+ .*{re.escape(name)}", text, re.MULTILINE | re.IGNORECASE), name
    for name in ("Gum measurements first", "Exam form first", "Stage 4 rule"):
        assert re.search(rf"^##+ .*{re.escape(name)}", text, re.MULTILINE | re.IGNORECASE), name


def test_doc_has_worked_examples_for_every_reader():
    kinds = {k for k, _, _ in _examples()}
    assert kinds == set(READ)


@pytest.mark.parametrize("kind,inp,status", _examples())
def test_each_worked_example_gives_the_status_the_code_gives(kind, inp, status):
    assert READ[kind](inp) == status


def test_readme_and_results_link_the_rules():
    for f in ("README.md", "docs/results.md"):
        assert "evidence_rules.md" in (REPO_ROOT / f).read_text(), f
