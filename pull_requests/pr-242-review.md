---
pr: 242
branch: chore/241-004-refresh-results-pages
title: "Refresh the results pages for every committed run since the last rebuild"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve-with-nits
---

# PR Review: Refresh the results pages for every committed run since the last rebuild

## Summary
Re-runs `28_ladder_vs_truth.py`, `29_medgemma_vs_bert.py` and `35_readme_results.py`, so the results pages include
three results PRs they had missed:
- #225: four GPU encoders;
- #210: MedGemma 4B v1;
- #229: the published `modernbert-base+cw` run.

The reviewer re-ran both seeded scripts, and the committed CSVs came out byte-identical. Recounting from
`ladder_vs_truth.csv` matches the pages.

The first review found prose beside the generated tables that the refresh had made stale. In one place the
conclusion had changed: MedGemma 1.5 4B's gap to the best encoder now has a CI that reaches 0. Those passages
are fixed in this PR. Two nits remain, below. Approve with nits.

## Scope of Change
- Files changed, excluding the generated ladder CSVs:
  - `docs/edr/README.md`, `docs/results.md` (generated tables, plus prose);
  - `docs/medgemma.md`, `docs/code_walkthrough.md`, `docs/model_inventory.md`;
  - `docs/claims.yaml`;
  - `python/tests/test_readme_results.py`.
- Generated: six files in `data/datasets/ladder/`.
- Areas touched: docs, data (generated), python tests.
- Range reviewed: `8527ffc..HEAD`.

## Secrets, PHI and Claims Scan
- Secrets: clean. The only "token" hit is a CSV column header.
- PHI: clean.
- Organization claims: clean.

## Findings

### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important): fixed in this PR
- **MedGemma 1.5 4B vs the best encoder** (`docs/edr/README.md`, `docs/medgemma.md`):
  - The text said "0.838 … difference -0.079 (-0.154 to -0.013)". The regenerated `medgemma_vs_bert.csv` gives
    0.825 and -0.067 (-0.138 to 0.000).
  - Both files now say the two can't be told apart on 240 charts, and add MedGemma 4B v1's comparison:
    -0.046 (-0.104 to 0.012); by difficulty 97 / 68 / 43%, where 1.5 gets 100 / 97 / 16%.
- **MedGemma 4B v1 shown as "not run; next"** (`docs/medgemma.md`, `docs/model_inventory.md`):
  - It is now marked run, with its own results paragraph.
  - The "next" section says the setup is done. I checked `models.yaml` (the Kaggle handle) and
    `kaggle/hf_config/medgemma-4b-it.*` before writing that.

### 🔵 Nits / suggestions (Minor)
- **Stale encoder status: fixed.**
  - `docs/edr/README.md` said "six encoders … CPU", and "the Longformers and large ModernBERTs need a GPU";
    `docs/code_walkthrough.md` said the same.
  - Both now say eleven encoders have results. The ranges were re-checked against `ladder_vs_truth.csv`:
    - alone, 77–83%, and every difference with the note rules has a CI that includes 0;
    - with the stage 4 rule (`+rules4`), 87–91%, and every CI excludes 0;
    - calibration error 0.14–0.18.
  - `docs/model_inventory.md` now marks ModernBERT large, BioClinical ModernBERT large, Longformer,
    Clinical-Longformer and MedGemma 4B as having results. The four left "not run yet" match the four on the
    results page.
- **The deck's 185 matched a row showing 77.1, not 185: fixed.** The claim now matches the exact
  `ladder_vs_truth.csv` row (accuracy 0.7708333 = 185/240).
- **Decks and README headline the older MedGemma: left for the owner.** These four places still use MedGemma
  1.5 4B's 185 of 240:
  - `docs/edr/slides/04-results.html`;
  - `docs/edr/full_text_and_notes.md`;
  - the EDR deck;
  - `README.md:28`.

  The EDR results page now shows MedGemma 4B v1 at 196. Each figure is correct and within its `covers`, and
  step 5 passes. Switching to 196 would change the slide's point ("about as good as keyword rules (189)"),
  so it is the owner's decision, not this refresh's.
- **The MedGemma version test doesn't check which run's numbers are shown: stays as is.**
  `test_readme_names_the_medgemma_version_that_ran` requires a version that ran and is not vacuous: an empty
  set or a bare "(MedGemma)" fails, as checked. It doesn't check that the version named is the one
  `readme_results.py` picked for its numbers; that pairing comes from one function, so a mislabel would need a
  code change there.

## Deck figures (rubric step 5)
- Re-derived 185: 0.7708333 × 240 = 185.
- The slide says "185 of 240 for MedGemma 1.5 4B untrained, with the same stage 4 rule: about as good as
  keyword rules (189)". That stays within its `covers`. Pass.

## Test Coverage
- `cd python && python -m pytest -q tests`: 962 passed, 15 skipped, after the fixes.
- Before the test and register changes, three tests failed: the two README checks that pinned the old numbers,
  and the deck register's 185.
- `35_readme_results.py --check`: clean.
- `ruff check tests/test_readme_results.py`: 11 findings, at lines 202–259, all already on `main`. None are in
  the changed lines.
- CI on the first head: all seven checks green.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | ✅ | |
| Synthetic only, no PHI | ✅ | |
| No organization claims; vendors cited | ✅ | |
| Test first | ✅ | No new behaviour; tests adjusted to say what they mean |
| Python and R in parity | n/a | No scoring or label change; CI `r-parity` green |
| Simulated is labelled simulated | ✅ | `--simulated` is still called a dry run |
| Seeds fixed | ✅ | Both scripts use `--seed 0` and reproduce byte for byte |
| Paths | n/a | |
| Spec for big changes | n/a | A results refresh only |
| Prices | n/a | |
| Deck figures | ✅ | 185 re-derived; slide within its covers |
| Commits | ✅ | `Closes #241`, co-author trailer |
| Docs | ✅ | Stale prose fixed (findings above) |
| Configuration, secrets register, idempotent writes, alerts | n/a | |

## Verdict
Approve with nits. All results are measurements on synthetic notes, not evidence about real records. Merge once
CI is green on the head.
