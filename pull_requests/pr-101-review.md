---
pr: 101
branch: docs/100-landing-two-paths
title: "Landing page with two paths, and an executive deck for the dental record path"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve
---

# PR Review: Landing page with two paths, and an executive deck for the dental record path

## Summary
The README becomes a short landing page under the working name Health Transformation Lab, with two paths: the
dental record (EDR) study, with a new 11-slide executive deck plus the study page for the science, and the lab,
with #98's pitch. The study README moves to `docs/edr/README.md` with every link working, and the results
generator follows it. The deck builder moves to `docs/build_decks.py` and builds every deck.

A fact-check found one critical framing error, which is fixed: the 234/240 headline belongs to the order that
reads gum measurements first, not to the exam-form-first order the deck showed. It also found unlabelled
simulated items and loose wording, now fixed. The verdict after fixes is approve.

## Scope of Change
- Files changed: about 35, mostly the new deck (11 slide sources, built HTML and text), two cover PNGs and the
  moved study page
- Areas touched: docs, python (results generator and tests)
- Commits:
  - d0e3014 Move the study README to docs/edr/README.md
  - 2328bb6 Landing page with two paths, and an executive deck
  - one commit with the review fixes and this file
- Range reviewed: `3b531da..HEAD` (stacked on #98)

## CI Status
| Check | Status |
|---|---|
| python | pending; 625 passed, 14 skipped locally |
| r-parity, bundle, postgres | pending; untouched |

## Secrets, PHI and Claims Scan
All three are clean.
- No organization's plan is described, and the ask names no partner. "No partner has been contacted" is now on
  the slide, not only in the notes.
- Company and literature claims are cited: Eke 2018, EFP/IDF, GlobalDentBench (averages over 12 models), and
  OHDSI.

## Strengths
- Every number traces to a committed source. The fact-check matched every figure on the landing page and in the
  deck, visible text and speaker notes.
- The landing page stays under 80 lines, and a test enforces it.
- The deck builder reproduces the pitch byte for byte, and tests check that the built files match their slides.
- A link check over every tracked markdown file (paths and anchors) finds 0 broken, the same as on the base.

## Findings
### 🔴 Blocking (Critical)
- **Fixed: slides 4 and 8 paired 234/240 with the wrong evidence order.**
  - Checked against `docs/results.md`: 234/240 (97.5%) is `algorithm_v0`, which reads gum measurements first.
    The study design's order, exam form first (`algorithm_design`), scores 72.1%, about 173 of 240.
  - Slide 8 is now "The order matters" and shows both. Slide 4 and the README say "gum measurements first".

### 🟡 Should fix (Important, non-blocking)
All fixed:
- **MedGemma and the stage 4 rule:** the 185 and 219 used a stage 4 rule that the slides didn't mention. Both
  now name it, and the notes give MedGemma's score without the rule (about 182).
- **185 vs 189:** the slide said "the same" as keyword rules; it now says "about as good as".
- **The 45 of 240 tile:** it sat among correct-answer scores but counted charts with no measurements. It now
  shows 193 of 240 right, with 45 charts that had no measurements.
- **Slide 3 reviewers:** the specialists' step now says the reviewers are simulated so far.
- **Slide 5:** "the largest models tried" is now "the largest models priced (simulated)".

### 🔵 Nits / suggestions (Minor)
Fixed:
- **Slide 9:** the acceptance bar now cites the OHDSI 2023 plenary as well.
- **Slide 6:** says "in its own environment", matching its notes.
- **README:** "large medical AI" is now "bigger", and the GlobalDentBench figures are given as averages over 12
  models.
- **Study page:** "while waiting for internal approvals" is removed.
- **`build_decks.py`:** an unknown deck name now exits with the valid names instead of a `KeyError` traceback.
- **The figure-labelling test:** it now also catches hours and dollars, and accepts only an explicit label or
  source. Any year no longer counts.

Left as is:
- **240 vs 233 charts:** slide 3 says 240 review charts and slide 5 uses the validation set as built (233), from
  `financial_tradeoffs.md`.
- **The study page's evidence table:** it describes the design order, while the leaderboard's best row is
  `algorithm_v0`. That predates this PR; action item A2 tracks the choice of order.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets, no PHI, no organization claims | ✅ | scans clean; #98's org-name test passes |
| Test first | ✅ | `test_decks.py` and the summary-link test were written before the code |
| Simulated labelled | ✅ | every figure slide says synthetic, illustrative or simulated, or cites a source (tested) |
| Paths | ✅ | the results generator uses `REPO_ROOT`; no hard-coded `data/` |
| Docs | ✅ | the README is a one-page landing page |

## Test Coverage
`cd python && pytest -q tests`: 625 passed, 14 skipped. `35_readme_results.py --check` is fresh. The link
check is clean. All 11 slides were rendered in Chromium with no overflow.

## Verdict
Approve, after the fixes above. Merge #98 first.
