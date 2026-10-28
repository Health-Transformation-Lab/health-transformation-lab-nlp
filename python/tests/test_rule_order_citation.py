"""Issue #192: the exam-form-first rule order (`algorithm_design`) names the paper it follows wherever it is defined,
and the gum-measurements-first order (`algorithm_v0`) says it is the repo's own."""

from health_transformation_lab_nlp.paths import REPO_ROOT

PAPER = "Patel et al., *Methods Inf Med* 2022"


def _section(path, heading):
    text = (REPO_ROOT / path).read_text(encoding="utf-8")
    start = text.index(heading)
    end = text.find("\n#", start + len(heading))
    return text[start:end if end != -1 else None]


def test_the_rules_page_cites_the_design_order_and_owns_v0():
    assert PAPER in _section("docs/evidence_rules.md", "### Rules, exam form first")
    assert "A2" in _section("docs/evidence_rules.md", "### Rules, exam form first")    # not yet checked
    assert "this repo's own" in _section("docs/evidence_rules.md", "### Rules, gum measurements first")


def test_the_walkthrough_and_the_code_cite_the_design_order():
    assert PAPER in _section("docs/code_walkthrough.md", "## 5. Rule-based phenotype")
    code = (REPO_ROOT / "python" / "health_transformation_lab_nlp" / "phenotype.py").read_text()
    comment = code[code.index("# Spec 005"):code.index("DESIGN_GROUPS")]
    assert "Patel et al. 2022" in comment and "Methods Inf Med" in comment


def test_the_reference_says_what_uses_it():
    ref = _section("docs/references.md", "4. **Patel JS, Brandon R")
    assert "algorithm_design" in ref and "phenotype.py" in ref and "algorithm_v0" in ref
