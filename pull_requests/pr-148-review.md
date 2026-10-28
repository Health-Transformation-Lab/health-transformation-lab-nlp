---
pr: 148
branch: chore/146-issue-title-keys
title: "Start every issue title with a Jira-style key"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator (docs-only, 1 file; no subagent needed)
verdict: approve
---

# PR Review: Start every issue title with a Jira-style key

## Summary
Extends the `NNN USn:` issue-title key that spec stories already use to every issue (action items,
fixes, chores, docs; `000` for repo-wide work), and requires unique spec numbers across `main` and open
PRs, after three specs claimed 019. One rule in `AGENTS.md`. Verdict: approve.

## Scope of Change
- Files changed: 2 (AGENTS.md, this review); +6
- Range reviewed: `origin/main..HEAD`

## Secrets, PHI and Claims Scan
Clean.

## Findings
None. 🔵 Issue titles aren't checked in CI; the PR conventions check covers branches and PR bodies only.

## Checks run
- `pytest -q tests -k "agent or convention"`: 41 passed, 1 skipped.
