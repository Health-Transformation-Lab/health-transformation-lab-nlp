---
pr: 210
branch: kaggle-results/medgemma-4b-it-40769250182
title: "Add MedGemma results from Kaggle (medgemma-4b-it)"
author: github-actions[bot]
reviewed_at: 2026-10-28
reviewer: coordinator verification against the Kaggle kernel output
verdict: approve
---

# PR Review: Add MedGemma results from Kaggle (medgemma-4b-it)

## Summary
The first full run of MedGemma 4B v1 on the 240 synthetic review notes, collected by the kaggle-medgemma
workflow ([run 14](https://github.com/healthtransformationlab/health-transformation-lab-nlp/actions/runs/40769250182),
from `main` at 8fbec7d, 46 minutes on Kaggle). The files are byte-identical to `kaggle kernels output
jcblearning/perio-bench-medgemma-reader`. The workflow pushed the branch but couldn't open the PR with its
token, so the PR was opened by hand. Approve.

## Scope of Change
- Files changed: 3 data files (+2,404), plus this review
  - `data/datasets/ai_predictions_medgemma-4b-it.csv`: 240 rows, one per visit
  - `data/datasets/llm_details_medgemma-4b-it.csv`: 240 rows (multi-line raw answers)
  - `data/datasets/results_manifest.csv`: two rows, `source = kaggle`, with the run URL
- Commits: 95aa86c Add MedGemma results from Kaggle (medgemma-4b-it); Review PR #210
- Range reviewed: `8fbec7d..HEAD`

## CI Status
| Check | Status |
|---|---|
| python, postgres, bundle, check | started by the review commit (a PR opened by the workflow token doesn't start CI) |

## What the run measured (synthetic notes; not evidence about real records)
| | medgemma-4b-it (this PR) | medgemma-1.5-4b-it (on main) |
|---|---|---|
| Visits | 240 | 240 |
| Gate pass | 226 (94.2%) | |
| Fallback (quote not in note) | 14 (5.8%) | |
| Exact status vs answer key | 77.9% | 75.8% |
| Median latency per note | 9.2 s (T4) | |

Every row names the weights as `keras/medgemma/keras/medgemma_instruct_4b/1`, converted on Kaggle
(`kaggle/keras_to_hf.py`, PR #186), with backend `hf`. The log shows 851 input and 97 output tokens per note.

## Secrets, PHI and Claims Scan
Clean.
- `raw` and `quote` hold text from the synthetic review notes only. Their names are placeholders such as
  `[NAME]` and `[ID]`.
- No credentials.
- The PR text calls the scores measurements on synthetic notes.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
None in this PR. Outside it, the workflow could not open its own PR, and its warning names the repo setting
(Settings → Actions → General → "Allow GitHub Actions to create and approve pull requests"). That setting is
the owner's to change. Until then, results PRs are opened by hand.

### 🔵 Nits / suggestions (Minor)
- The README leaderboard isn't refreshed here. It is refreshed after the merge with
  `scripts/28_ladder_vs_truth.py` and `35_readme_results.py`, as the workflow's PR text says.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets / PHI / org claims | ✅ | |
| Simulated is labelled simulated | ✅ | real model output on synthetic notes, not `sim:` |
| Idempotent writes | ✅ | Load results is keyed by file SHA-256 (spec 016) |
| Rows carry batch key | ✅ | manifest row with the run URL; Load results adds `file_sha256` and `loaded_ts` |
| Other rows | n/a | |

## Verdict
approve. Merge once CI is green. Load results needs Databricks dev, which is refusing new runs (2026-10-28).
