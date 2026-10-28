"""Branch names and issue links on pull requests (.github/scripts/pr_conventions.py, AGENTS.md)."""

import importlib.util

import pytest

from dental_omop_nlp.paths import REPO_ROOT

_spec = importlib.util.spec_from_file_location("pr_conventions", REPO_ROOT / ".github" / "scripts" / "pr_conventions.py")
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)


@pytest.mark.parametrize("branch", [
    "feat/71-016-results-loader",       # issue 71, spec 016's user story
    "fix/72-volume-log-append",
    "docs/80-branch-naming",
    "data/81-nhanes-2015",
    "ci/82-pr-conventions",
    "chore/83-bump-kaggle-cli",
    "spec/84-017-pipeline-doctor",
    "feat/DENT-123-results-loader",     # a Jira key works too
])
def test_good_branch_names(branch):
    assert pc.branch_problems(branch) == []


@pytest.mark.parametrize("branch, why", [
    ("my-branch", "type"),
    ("feature/71-x", "type"),                       # feat, not feature
    ("feat/results-loader", "issue"),               # no ticket
    ("feat/71-Results_Loader", "lowercase"),
    ("feat/71-" + "x" * 50, "long"),
    ("003-radiograph-structured-data", "type"),     # Spec Kit's default: needs the type and issue
])
def test_bad_branch_names_say_why(branch, why):
    problems = pc.branch_problems(branch)
    assert problems and why in " ".join(problems).lower()


@pytest.mark.parametrize("branch", ["claude/great-cerf-qwbqck", "dependabot/pip/pandas-3.0", "kaggle-results/medgemma-1.5-4b-it-123"])
def test_branches_named_by_a_tool_are_allowed(branch):
    assert pc.branch_problems(branch) == []


@pytest.mark.parametrize("body", ["Closes #71", "fixes #72.", "Part of the work.\n\nRefs #73", "Closes DENT-123", "Resolves #9"])
def test_issue_link_found(body):
    assert pc.issue_link(body)


@pytest.mark.parametrize("body", ["", None, "See issue 71", "#71 only mentioned", "Closes 71"])
def test_no_issue_link(body):
    assert not pc.issue_link(body)


def test_check_needs_an_issue_link_except_on_tool_branches():
    assert pc.check("feat/71-x", "Closes #71") == []
    assert pc.check("claude/great-cerf-qwbqck", "Closes #71") == []
    assert any("issue" in p.lower() for p in pc.check("claude/great-cerf-qwbqck", "no link"))
    assert any("issue" in p.lower() for p in pc.check("feat/71-x", ""))
    assert pc.check("kaggle-results/x-1", "") == []          # made by a workflow from a run, not a story
    assert pc.check("dependabot/pip/x", "") == []


def test_workflow_runs_the_check_on_every_pr_without_interpolating_text():
    import yaml
    text = (REPO_ROOT / ".github" / "workflows" / "pr-conventions.yml").read_text()
    wf = yaml.safe_load(text)
    on = wf.get("on", wf.get(True))
    assert "pull_request" in on and "edited" in on["pull_request"]["types"]
    run = " ".join(s.get("run", "") for s in wf["jobs"]["check"]["steps"])
    assert "pr_conventions.py" in run
    assert "${{" not in run              # branch and body reach the script via env, never pasted into shell


def test_rule_is_written_down_for_every_agent():
    agents = (REPO_ROOT / "AGENTS.md").read_text()
    assert "## Branches and issues" in agents and "Closes #" in agents
    assert "Branches and issues" in (REPO_ROOT / "CLAUDE.md").read_text()
