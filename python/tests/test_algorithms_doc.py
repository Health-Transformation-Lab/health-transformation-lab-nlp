"""Issue #209: docs/algorithms.md lists every method that assigns a periodontal status, with its source (a citation
or "this repo's own") and its accuracy, which must match docs/results.md."""

import re

from health_transformation_lab_nlp import readme_results as rr
from health_transformation_lab_nlp.paths import REPO_ROOT

DOC = REPO_ROOT / "docs" / "algorithms.md"


def _rows():
    rows = {}
    for line in DOC.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`([^`]+)`", line)
        if m:
            rows[m.group(1)] = [c.strip() for c in line.strip().strip("|").split("|")]
    return rows


def _results():
    acc = {}
    for line in (REPO_ROOT / "docs" / "results.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*[\d–]+\s*\|\s*\[?`([^`]+)`.*?\*\*([\d.]+)\*\* \(([\d.]+)–([\d.]+)\)", line)
        if m:
            acc.setdefault(m.group(1), f"{m.group(2)} ({m.group(3)}–{m.group(4)})")
    return acc


def test_every_rule_phenotype_and_evidence_reader_has_a_row():
    missing = (set(rr.PHENOTYPES) | set(rr.EVIDENCE) | {"note_rules"}) - set(_rows())
    assert not missing, f"document these in docs/algorithms.md: {sorted(missing)}"


def test_every_row_names_its_source():
    for name, cells in _rows().items():
        source = cells[3]
        assert re.search(r"this repo's own|\[\[\d+(, \d+)*\]\]\(#sources\)", source), (name, source)


def test_every_cited_number_is_in_the_sources_list_with_its_full_reference():
    text = DOC.read_text(encoding="utf-8")
    listed = text[text.index("## Sources"):]
    refs = (REPO_ROOT / "docs" / "references.md").read_text(encoding="utf-8")
    for group in re.findall(r"\[\[([\d, ]+)\]\]\(#sources\)", text):
        for n in group.split(", "):
            first_author = re.search(rf"^{n}\. \*\*([^,.*]+)", refs, flags=re.M).group(1)
            entry = re.search(rf"^{n}\. (.+)$", listed, flags=re.M)
            assert entry and entry.group(1).startswith(first_author), (n, first_author)


def test_every_number_matches_the_results_page():
    acc = _results()
    for name, cells in _rows().items():
        shown = cells[4]
        if name in acc:
            assert shown == acc[name], (name, shown, acc[name])
        else:
            assert "not in the leaderboard" in shown or "not built yet" in shown, (name, shown)
