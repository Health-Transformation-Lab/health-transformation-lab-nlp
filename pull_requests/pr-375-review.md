---
pr: 375
branch: chore/374-copy-decks-to-site
title: "Copy the built decks to the website when they change on main"
author: jcbowyer
reviewed_at: 2026-10-30
reviewer: coordinator (workflow, script, tests, register)
verdict: approve
---

# PR Review: Copy the built decks to the website

## Summary
A workflow copies the built decks and covers to the site repository whenever they change on main. Verdict:
approve. It waits on the owner's `SITE_DEPLOY_TOKEN`.

## Scope of Change
- Commits: d4fb53e
- Range reviewed: `origin/main..d4fb53e`

## Rubric
- **Settings checked first:** the token's shape, then one API call that it can push, before cloning.
- **Idempotent:** it commits only when a file changed; a test proves a second run is empty.
- **Secrets:** the token is only in env and the clone URL, never printed. Registered with scope and owner; expiry
  unknown until made.
- **Least privilege:** fine-grained, one repository, Contents read and write.
- **Tests first:** `test_site_decks.py`.

## Risks
- If the site's `main` gets branch protection, the push is refused and the run fails visibly. Switch to opening a
  PR then.
- If the site changes its icon links, update `ICONS` here, or the next copy reverts them.

## CI Status
| Check | Status |
|---|---|
| python | 1117 passed, 16 skipped locally |
