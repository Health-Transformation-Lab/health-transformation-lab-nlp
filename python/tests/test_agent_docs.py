"""AGENTS.md holds the rules every coding agent follows; CLAUDE.md imports it and adds only Claude Code's
own workflow, so the rules live in one place."""

from dental_omop_nlp.paths import REPO_ROOT

AGENTS = REPO_ROOT / "AGENTS.md"
CLAUDE = REPO_ROOT / "CLAUDE.md"
RULES = ("Synthetic only. No PHI, ever.", "Python and R stay in parity.", "Test first.",
         "Label simulated output as simulated.", "never use\n  `mode: development`", "| Credential | Where it's made |")


def test_agents_md_has_every_shared_rule():
    text = AGENTS.read_text()
    for heading in ("## Ground rules", "## When a change needs a spec", "## Commands", "## Conventions"):
        assert heading in text, heading
    for rule in RULES:
        assert rule in text, rule


def test_claude_md_imports_agents_md_and_does_not_repeat_it():
    text = CLAUDE.read_text()
    assert "@AGENTS.md" in text.split("##")[0]                    # imported before any section
    for rule in RULES:
        assert rule not in text, rule                              # one copy only: AGENTS.md
    assert "Superpowers" in text and "/speckit-specify" in text     # Claude Code's own workflow stays here


def test_reviews_check_against_both_files():
    for f in (".claude/review-rubric.md", ".claude/commands/pr-review.md"):
        assert "AGENTS.md" in (REPO_ROOT / f).read_text(), f
