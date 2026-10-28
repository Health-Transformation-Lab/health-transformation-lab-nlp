---
pr: 162
branch: docs/161-periobench-deck-outcome
title: "PerioBench deck: lead with better gum-disease care"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator (docs-only, one slide; no subagent needed)
verdict: approve
---

# PR Review: PerioBench deck: lead with better gum-disease care

## Summary
This PR rewords the PerioBench deck's cover slide and its speaker notes around better care for people with
periodontitis through more accurate diagnosis. Agreement with gum specialists is described as how accuracy is
checked, not the goal. The deck title in `docs/build_decks.py` now names PerioBench. The two decks and the
landing cover image are rebuilt. Verdict: approve.

## Scope of Change
- Files changed: 6 (docs and the deck builder's title string)
- Areas touched: docs/edr, docs/img, docs/build_decks.py, pull_requests
- Commits:
  - 2d8535b PerioBench deck: lead with better gum-disease care
- Range reviewed: `origin/main..2d8535b`

## Rubric
- Synthetic only, no PHI: yes. The cover still says synthetic records.
- Simulated output labelled: no new figures.
- Org names: `test_no_org_references` passes.
- Generated files match their sources: `deck.html` and `full_text_and_notes.md` are rebuilt by `build_decks.py`.
- Python/R parity: not affected.

## CI Status
| Check | Status |
|---|---|
| check (branch and issue) | pending |
| python, r-parity | skipped (docs only); `test_decks` and `test_no_org_references`: 8 passed locally |

## Findings
None blocking. The cover PNG is a rendered screenshot that no script rebuilds. If the cover changes again, it has
to be re-rendered by hand, as it was here.
