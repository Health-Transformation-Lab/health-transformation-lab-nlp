---
pr: 98
branch: claude/databricks-token-pr-merge-xjbpfa
title: "Add the Shark Tank pitch as a generic personal idea; never reference one organization"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator (docs and one check)
verdict: approve
---

# PR Review: the pitch, and the organization-name rule

## Summary
Closes #91 and #96. It adds `docs/pitch/`: 24 slide sources, `build.py`, and the deck and full text built from
them. It also removes one organization's name from four docs, states the rule in `CLAUDE.md` (the only file
allowed to name it), and adds a test that enforces the rule.

## Findings
None blocking.

- 🔵 Five arXiv IDs on the "tests" slide (2603.08281, 2505.06046, 2511.04705, 2406.06056, 2403.12025) were kept as
  the author had them. arxiv.org was not reachable from the review session, so the review didn't check them.
- Risk: the rule covers files at the current commit only. Earlier commits in git history still hold the old
  disclaimer and citation lines.

## Checks
- `pytest -q tests`: 618 passed, 14 skipped, after merging `main`.
- `test_no_org_references.py` failed before the change, and it caught a planted mention. It doesn't match
  "access-to-care questions".
- All 24 slides were rendered in Chromium; none overflows its frame.
- Scans: no secrets, no PHI, no real data. Figures in the pitch name their public source. No partner is described
  as contacted or agreed.

## Compliance
| Rule | Result |
|---|---|
| No secrets, synthetic only, no organization claims; vendors cited | Pass |
| Organization names (CLAUDE.md) | Pass (enforced by test) |
| Test first | Pass |
| Spec for big changes | Not needed (docs and one check) |
| Branches and issues | Pass (`claude/*` branch, `Closes #91`, `Closes #96`) |
