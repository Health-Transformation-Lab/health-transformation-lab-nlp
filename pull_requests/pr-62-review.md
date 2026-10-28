---
pr: 62
branch: claude/great-cerf-qwbqck
title: "Run MedGemma on Kaggle from GitHub, and load every result into the gold tables (spec 016)"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve after fixes
---

# PR Review: Run MedGemma on Kaggle from GitHub, and load every result into the gold tables (spec 016)

## Summary
The review raised two Important findings and three Minor ones. All five held up when checked against the
code and are fixed on the branch, each with a test. Scans found no secrets, no PHI and no organization
claims. The result rows are model answers on the 240 synthetic review notes, and `simulated_*` files are
excluded from both recording and loading.

## Scope of Change
- Areas touched: Kaggle workflow and notebook, `kaggle/` scripts, `results_store.py`, Databricks notebooks 03 and 10,
  the `load_results` job, `deploy.yml`, docs, spec 016
- Range reviewed: `origin/main...HEAD`

## Findings and outcome
| # | Severity | Finding | Outcome |
|---|---|---|---|
| 1 | 🟡 Important | A 10-note test run under a new method name (`+k2` for shots, or a new rung) had no committed file to compare with, so a PR was opened with 10 rows | Fixed: `record_results.py --min-rows`, defaulting to the answer key's 240 notes; test added |
| 2 | 🟡 Important | Appends commit one at a time: a failure after `ai_predictions` left no `result_files` row, so the next deploy duplicated predictions | Fixed: each append first deletes rows of the same file versions (guarded for the reader job's rows without `sha256`) |
| 3 | 🔵 Minor | Casting every column to the table's type could turn real `error` text into null | Fixed: only all-empty columns are cast; a real clash fails loudly. The reader job now writes empty columns as text |
| 4 | 🔵 Minor | `show_log.py` dropped the line after any one-line warning | Fixed: only an indented source line is dropped; test case added |
| 5 | 🔵 Minor | `always()` ran the PR step on a cancelled run | Fixed: `!cancelled()` |

## Checks
- `python -m pytest -q tests`: 544 passed, 12 skipped. `ruff check` on changed Python files: clean. Notebook 03's
  existing I001/RUF100 findings are the same on `main`.
- CI on the previous head: python, r-parity, postgres, bundle and azure-infra all green. The red `run`
  checks are the manual Kaggle workflow, which stops at the notebook's HF_TOKEN step (account setup, not code).
- Load notebook run twice on local Spark 3.5 with a fake `dbutils`: 16 files, 3,600 prediction rows and 240
  LLM rows; the second run added nothing. Delta-only steps (`DELETE`, `mergeSchema`) couldn't be run here,
  because the Delta jars couldn't be downloaded; they run first in dev.
- PR step dry-run against a local bare remote with `gh` stubbed: one commit with the two CSVs and the manifest.

## Compliance
| Rule | Result | Note |
|---|---|---|
| No secrets | Pass | Kaggle token only via `GITHUB_ENV` from secrets |
| Synthetic only, no PHI | Pass | Model output on synthetic notes |
| No organization claims | Pass | |
| Test first | Pass | Each behaviour, including every fix, has a test |
| Python/R parity | n/a | No label, scoring, reliability or cost change |
| Simulated is labelled | Pass | `simulated_*` never recorded or loaded |
| Seeds fixed | n/a | |
| Paths | Pass | `DATASETS_DIR` |
| Spec for big changes | Pass | `specs/016-results-to-databricks/` with spec, plan, tasks, revision |
| Prices | n/a | |
| Commits | Pass | Merge commit 1c94d1b has no body (merge of already-squashed history) |
| Docs | Pass | `results_storage.md`, `deployment.md` |
