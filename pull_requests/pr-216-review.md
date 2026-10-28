---
pr: 216
branch: docs/207-deck-claims
title: "Price the decks' software cost by model; register every slide figure"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve-with-nits
---

# PR Review: Price the decks' software cost by model; register every slide figure

## Summary
The PerioBench economics slide said "Computers are cheap" and put a million notes at hundreds of dollars "even for
the largest models priced". This PR prices software by model instead, from under $15 to about $1.2M, with dated list
prices and the assumptions marked. It adds `docs/claims.yaml`, a register of every slide figure, and a test that
holds the slides to it. The reviewer re-derived every cost tier and every measured figure: all hold. The findings
were wording that still claimed a little more than the sources show, and gaps in the test. All are fixed on the
branch, as is the same kind of wording in the pitch deck. Approve with nits.

## Scope of Change
- Files changed: the economics slide and four pitch slides, the rebuilt decks and full texts, `docs/claims.yaml`,
  `python/tests/test_deck_claims.py`, `.claude/review-rubric.md`, `docs/financial_tradeoffs.md`, a comment in
  `costs.yaml`, this review
- Areas touched: docs (decks, register, rubric), python (tests), config (a comment only)
- Range reviewed: `origin/main...docs/207-deck-claims`

## CI Status
| Check | Status |
|---|---|
| Check the branch name and issue link | see the PR's checks on the head |
| Test every change (python, postgres, r-parity, bundle) | see the PR's checks on the head |

## Secrets, PHI and Claims Scan
- Secrets: clean. PHI / real data: clean.
- Organization claims: vendors are named only with their own published prices (claude.com/pricing, Databricks),
  each with the date checked.

## Strengths
- Re-derived by the reviewer:
  - 103 tokens a note, from the committed `sim:llm_challenger` cost;
  - $256.5 (Llama 3.3 70B), $5,530 (Fable 5.1, the note only) and $1.2M (whole record, three calls);
  - $13.41 for ModernBERT, so "under $15" holds.
- Every `measured` entry's match string is the row that reports that figure, not a coincidental hit.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
1. `docs/edr/slides/05-economics.html` notes: said the note's token count was "measured", but it is chars ÷ 4 and
   the prompt and answer lengths are assumed. **Fixed:** "estimated … characters divided by four … assumed".
2. Same notes: "five orders of magnitude" (×89,000, 4.95 orders, with an illustrative low end). **Fixed:** "from
   under 15 dollars to about 1.2 million, depending on the model".
3. `costs.yaml`: `llm_challenger` was still labelled ILLUSTRATIVE, but the slide quotes its price as the Databricks
   list price. That price matches the list price the file's de-identification section cites, with a date.
   **Fixed:** the comment names that source, and keeps the prompt and output lengths marked ASSUMED. Only the
   comment changed, no number, so there is no cost or parity change.

### 🔵 Nits / suggestions (Minor)
1. The test missed "41" in "41 of 2,462" and "20k"/"4k" on the slides. **Fixed:** the figure pattern now matches
   counts before "of" and "k" thousands, and the register has entries for 41, 20k and 4k.
2. `cheap` didn't match "cheaply". **Fixed** (`cheap\w*`). It caught "we learned that cheaply" in the pitch's notes,
   now "at small cost".
3. "Proving any of them is good enough is small" implied one test fits every model. **Fixed:** "The acceptance test
   is small".
4. The "$15" entry didn't name its assumptions. **Fixed:** 150 notes/s, 1.5 h training, $4/GPU h, all assumed.
5. `docs/financial_tradeoffs.md` said every row is "a short prompt", but the local encoders take no prompt.
   **Fixed:** "reads only the note".
6. Speaker notes aren't scanned for figures, only for absolute wording. Kept: registering every number in the notes
   is a larger job, so the register's header says the gap is there and the rubric's deck step covers the notes by
   hand.
7. A bare count such as 2000 would read as a year and be skipped. Kept: no deck has one, and treating it as a figure
   would flag every year.

### Also fixed in the pitch deck (same issue)
The pitch's slides made absolute claims their own notes hedge ("a first search, not a full review"):
- "no one tests whether…" is now "no test we found checks whether…";
- "No scorecard checks…" is now "No scorecard we found checks…";
- "every leading AI is graded" is now "every AI model tested on that scorecard";
- "the AI companies have to answer" is now "harder … to ignore";
- "compete to fix it" is now "have a reason to fix it".

The test now flags those phrases.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | ✅ | |
| Synthetic only, no PHI | ✅ | |
| No organization claims; vendors cited | ✅ | Prices cite the vendor's own page, with the date |
| Test first | ✅ | `test_deck_claims.py` fails on the old slides ("Computers are cheap", and the pitch's "no one tests") |
| Python and R in parity | ✅ | No change to cost logic or numbers |
| Simulated is labelled simulated | ✅ | Illustrative and assumed figures marked on the slide and in the register |
| Seeds fixed | n/a | |
| Paths | ✅ | Test uses `REPO_ROOT` |
| Spec for big changes | n/a | Docs accuracy; issue #207 |
| Prices | ✅ | Each price names its source and date |
| Deck figures | ✅ | Register complete for the slides; external figures not re-checked are marked `checked: null` |
| Commits | ✅ | |
| Docs | ✅ | Decks rebuilt and match the builder |

## Test Coverage
- `cd python && python -m pytest -q tests`: 910 passed, 15 skipped. `ruff check` on the new test: clean.
- Slide 5 rendered in Chromium: no overflow, and the content ends inside the margin.
- External figures re-checked against their source today: CDC 1.9M only. The others are `checked: null`, because
  arxiv.org, pubmed, openai.com and ai.google.dev are blocked from this environment.

## Verdict
**Approve with nits.** Merge once CI is green on the head. A follow-up should re-check the `checked: null` citations
from a machine that can reach the sources.
