"""Check a pull request's branch name and issue link (the rule in AGENTS.md, "Branches and issues").

    <type>/<ticket>-<slug>      feat/71-016-results-loader, fix/72-volume-log-append, feat/DENT-123-loader
    type     feat fix docs data ci chore spec
    ticket   a GitHub issue number, or a Jira key (DENT-123)
    slug     lowercase words joined by '-', at most 40 characters; spec work starts with the spec number

Branches a tool names are allowed as they are: dependabot/*, kaggle-results/* (the Kaggle workflow's results
PRs). An agent session's assigned claude/* branch is not: the session moves its work to <type>/<issue>-<slug>
(AGENTS.md rule 4, issue #116). Every PR except dependabot's and kaggle-results' links its issue in the body:
"Closes #71" (or Fixes, Resolves, Refs; or a Jira key).

Usage in CI: BRANCH=... BODY=... python .github/scripts/pr_conventions.py
"""

import os
import re
import sys

TYPES = ("feat", "fix", "docs", "data", "ci", "chore", "spec")
TOOL_BRANCHES = ("dependabot/", "kaggle-results/")
NO_ISSUE_NEEDED = ("dependabot/", "kaggle-results/")
TICKET = r"(?:\d+|[A-Z][A-Z0-9]+-\d+)"
LINK = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?|refs?)\s+(?:#\d+|[A-Z][A-Z0-9]+-\d+)\b", re.IGNORECASE)
MAX_SLUG = 40


def branch_problems(branch: str) -> list[str]:
    if branch.startswith(TOOL_BRANCHES):
        return []
    if branch.startswith("claude/"):
        return [(f"'{branch}' is an agent session's assigned branch: open or find the issue, then push the work to "
                 "<type>/<issue>-<slug> and open the PR from there (AGENTS.md, Branches and issues, rule 4)")]
    kind, _, rest = branch.partition("/")
    if kind not in TYPES or not rest:
        return [f"start with a type and '/': one of {', '.join(TYPES)} (got '{branch}')"]
    m = re.fullmatch(rf"({TICKET})-(.+)", rest)
    if not m:
        return [f"put the issue number (or Jira key) after the type: {kind}/<issue>-<slug>"]
    slug = m.group(2)
    problems = []
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        problems.append(f"slug must be lowercase words joined by '-' (got '{slug}')")
    if len(slug) > MAX_SLUG:
        problems.append(f"slug too long: {len(slug)} characters, at most {MAX_SLUG}")
    return problems


def issue_link(body: str | None) -> bool:
    return bool(body and LINK.search(body))


def check(branch: str, body: str | None) -> list[str]:
    problems = branch_problems(branch)
    if not branch.startswith(NO_ISSUE_NEEDED) and not issue_link(body):
        problems.append("link the issue in the PR description: 'Closes #<issue>' (or Fixes, Refs, or a Jira key)")
    return problems


if __name__ == "__main__":
    branch, body = os.environ.get("BRANCH", ""), os.environ.get("BODY", "")
    found = check(branch, body)
    for p in found:
        print(f"::error::{p}")
    if not found:
        print(f"'{branch}' and its issue link follow AGENTS.md")
    sys.exit(1 if found else 0)
