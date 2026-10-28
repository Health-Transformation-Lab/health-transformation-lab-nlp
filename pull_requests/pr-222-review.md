---
pr: 222
branch: docs/221-drop-working-name
title: "Drop \"working name\" from the README headline and deck covers"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator (docs-only wording change; no code)
verdict: approve
---

# PR Review: Drop "working name" from the README headline and deck covers

## Summary
This removes "working name" from the README banner, the pitch README and both deck covers. The decks are rebuilt
with `docs/build_decks.py`. The disclaimers keep everything else they said: a personal learning project, not
affiliated, not any organization's plan, synthetic data only. Docs only. Verdict: approve.

## Scope of Change
- Files changed: 8 (README, pitch README, two cover slides, and each deck's built `deck.html` and
  `full_text_and_notes.md`)
- Commits: `072641e` Drop "working name" from the README headline and deck covers

## Secrets, PHI and Claims Scan
Clean. No organization is named; the disclaimer wording on affiliation is unchanged.

## Findings
None.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets, no PHI, no organization claims | ✅ | |
| Docs | ✅ | the built decks match their slides (`test_decks.py`) |
| Branch and issue | ✅ | `docs/221-...`, `Closes #221` |

## Test Coverage
`pytest -q tests`: 848 passed, 14 skipped. `git grep -i "working name"` finds no current file, outside `specs/`
and `pull_requests/`.

## Verdict
**approve.** Merge when CI is green.
