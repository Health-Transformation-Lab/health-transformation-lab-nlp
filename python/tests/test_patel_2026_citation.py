"""Issue #194: reference 53 (Patel et al. 2026, linked medical and dental records) is cited with what was checked,
and spec 013's G10 and G11 name it, say what G10 could adopt, and hand the medical-record side to spec 023."""

from health_transformation_lab_nlp.paths import REPO_ROOT


def _entry(path, start, stop):
    text = (REPO_ROOT / path).read_text(encoding="utf-8")
    begin = text.index(start)
    return text[begin:text.index(stop, begin + len(start))]


def test_reference_53_is_the_2026_paper_checked_on_pubmed():
    ref = _entry("docs/references.md", "53. **Patel JS", "\n## ")
    for fact in ("Tellez M", "JDR Clin Trans Res 2026;11(4):555–570", "10.1177/23800844251408849",
                 "PMID 41673528", "PMC13292087"):
        assert fact in ref


def test_reference_53_notes_the_papers_inconsistencies():
    ref = _entry("docs/references.md", "53. **Patel JS", "\n## ")
    assert "106" in ref and "109" in ref                      # abstract vs Methods
    assert "67/85/84" in ref and "66/86/84" in ref and "66/86/86" in ref   # abstract vs Table 2, experiment 1


def test_spec_013_g10_and_g11_cite_it_and_point_to_spec_023():
    g10 = _entry("specs/013-literature-methods/spec.md", "| G10 |", "\n")
    g11 = _entry("specs/013-literature-methods/spec.md", "| G11 |", "\n")
    assert "Patel et al. 2026" in g10 and "Patel et al. 2026" in g11
    for adopt in ("healthy, I, II, III+IV", "70/30 stratified", "Brier", "PROBAST", "TRIPOD-AI"):
        assert adopt in g10
    assert "spec 023" in g11
