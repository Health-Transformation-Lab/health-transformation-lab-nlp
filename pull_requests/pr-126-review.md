---
pr: 126
branch: feat/120-020-kaggle-publish
title: "Publish the synthetic notes and benchmark results as Kaggle datasets"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve-with-nits
---

# PR Review: Publish the synthetic notes and benchmark results as Kaggle datasets

## Summary
Spec 020 US1, US2 and US4. `kaggle/publish.py` builds two public CC BY 4.0 Kaggle datasets from a fixed set of
files: the synthetic notes and charts, and every real model's results on the review set. A data card written in
`kaggle/cards/` carries the disclaimer. The `kaggle-publish` workflow creates each dataset the first time and
adds a version after that. `kaggle/README.md` explains everything on Kaggle in one page.

Review found no blocking issue and two important ones:
- a refused upload passed as a success, because the Kaggle CLI only prints the error;
- nothing stopped a partial (`--limit`) or simulated-row file from being published under a normal name.

Both are fixed on the branch with tests, along with four minor points. These datasets go public, so the fixes
went in before the first publish. Verdict: approve-with-nits.

## Scope of Change
- Files changed: 10 (+~560), no generated data
- Areas touched: kaggle, ci (new workflow), python tests, specs, docs (README, cards)
- Commits:
  - `46afb65` Publish the synthetic notes and benchmark results as Kaggle datasets
  - (this commit) Fail refused uploads; refuse partial or simulated files; card and spec fixes; review
- Range reviewed: `origin/main (0ec3284)..HEAD`

## CI Status
| Check | Status |
|---|---|
| python, postgres, r-parity, bundle, azure-infra, check | running on `46afb65` when reviewed; re-run on this commit |

## Secrets, PHI and Claims Scan
- **Secrets:** clean. Credentials come from GitHub secrets through `env`, the same way as the existing Kaggle
  workflows.
- **PHI / real data:** clean. The reviewer built both folders (6 and 29 files) and grepped them. Nothing comes
  from `data/external/` or `data/raw/`, and there is no `simulated_*` file. The only `simulated` hit is
  `judge/judgments.csv`'s column header, and its values are all False.
- **Organization claims:** clean. The cards say the project is unaffiliated, in line with `DISCLAIMER.md`, and
  name no organization.

## Strengths
- Inputs reach the shell only through quoted `env` variables, and `dataset` is a choice input, so there is no
  injection path.
- `permissions: contents: read` and `concurrency` are set.
- The file list is explicit. Tests check that the built folder holds exactly those files and that the card
  lists every one.
- The card's contents table is generated from the files, so row counts can't drift.
- The README's workflow names, inputs and error messages match the actual workflows.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
- **A refused upload passed as a success.** `kaggle-publish.yml`, build-and-publish step.
  - In kaggle 2.2.5, `dataset_create_new_cli` and `dataset_create_version_cli` print "creation error" and
    return. The process exits 0, and on a version with invalid tags it doesn't even print the status.
  - Verified in the 2.2.5 source.
  - **Fixed:** `publish.py --upload` calls the Python API (`dataset_create_new` / `dataset_create_version`) and
    fails unless `result.status` is ok. Invalid tags only warn. The workflow uses `set -o pipefail` around
    `tee`. Four tests use a fake API.
- **Partial or simulated files under normal names.** `publish.py`, `files_of`.
  - `11_ai_predict.py --limit N` writes the same `ai_predictions_<rung>.csv`, and a `sim:` row could sit in a
    non-prefixed file in `ladder/` or `judge/`.
  - **Fixed:** `check()` runs in `build()` and refuses any prediction or LLM-details file whose row count isn't
    the full review set, and any `sim:` or `calib:` value. Tests run it on today's files and on a planted
    1-row file.

### 🔵 Nits / suggestions (Minor)
- **Tags Kaggle may not know** ("text classification", "model comparison") would be dropped silently.
  **Fixed:** they're now `nlp`, `health` and `medicine`, and unknown tags are reported.
- **FR-001 said "not globbed", but the results list is globbed** within named folders. **Fixed:** the spec now
  says what the code does and adds FR-004 (refused uploads fail).
- **Hard-coded `data/datasets` path.** **Fixed:** the script uses `dental_omop_nlp.paths.DATASETS_DIR`, and the
  workflow installs the package.
- **Results card gaps.** It didn't mention the classical model (TF-IDF with logistic regression) or say the
  cost columns are illustrative. **Fixed:** both added. The rates are the placeholders in `costs.yaml` (marked
  ILLUSTRATIVE) and the judge endpoint's per-token price, not quotes.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | ✅ | |
| Synthetic only, no PHI | ✅ | generated data only; `data/external` excluded by code and test |
| No organization claims; vendors cited | ✅ | |
| Test first | ✅ | the builder tests and the review-fix tests each failed before their code |
| Python and R in parity | n/a | no label or scoring change |
| Simulated is labelled simulated | ✅ | simulated files and rows refused |
| Seeds fixed | n/a | |
| Paths | ✅ after fix | `DATASETS_DIR` |
| Spec for big changes | ✅ | spec 020, issues #120–#123, branch `feat/120-020-kaggle-publish` |
| Prices | ✅ after fix | the card says the cost columns are illustrative |
| Commits | ✅ | |
| Docs | ✅ | `kaggle/README.md`; the cards are the dataset pages |

## Test Coverage
`tests/test_kaggle_publish.py` has 16 tests:
- files exist and are not simulated or external;
- the built folder matches the list exactly;
- metadata: licence, length limits, card contents and commit;
- the workflow;
- full-run row counts;
- no `sim:` or `calib:` rows;
- a partial file is refused;
- upload creates the first time and versions after;
- upload fails on an error or a None result;
- invalid tags warn.

The full suite passes: 664 passed, 14 skipped. Not run here: the workflow itself, which can only be started
once it is on `main`. The first publish after merge is the end-to-end check (spec 020 T005).

## Verdict
**approve-with-nits.** Every finding is fixed on the branch. Merge when CI is green on the head commit, then
run *Publish datasets to Kaggle* with `both` and check both pages.
