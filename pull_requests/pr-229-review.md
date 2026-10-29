---
pr: 229
branch: kaggle-results/encoders-40763974247
title: "Add GPU encoder results from Kaggle (modernbert-base+cw, the published model's run)"
author: github-actions[bot]
reviewed_at: 2026-10-28
reviewer: coordinator verification against the Kaggle kernel log (version 4)
verdict: approve
---

# PR Review: Add GPU encoder results from Kaggle (modernbert-base+cw, the published model's run)

## Summary
[Run 4](https://github.com/healthtransformationlab/health-transformation-lab-nlp/actions/runs/40763974247), from
`main` at 6b744b3, did three things:
- retrained the class-weighted ModernBERT-base (seed 42, 3 epochs) on Kaggle's T4s, in 11 minutes;
- saved its predictions;
- published the weights as the Kaggle model ("Publish the model to Kaggle": success).

This PR replaces the committed predictions with that run's, so the repo's file is the published model's own.
Approve.

## Scope of Change
- `data/datasets/ai_predictions_modernbert-base+cw.csv`: 240 rows, replaced
- `data/datasets/results_manifest.csv`: one row, `source = kaggle`, with the run URL
- Range reviewed: `6b744b3..HEAD`

## What changes (synthetic notes; not evidence about real records)
| | Exact status vs answer key |
|---|---|
| file on main (earlier run) | 83.8% |
| this run (the published model) | 82.5% |

Same seed, different hardware and run: GPU training isn't bit-reproducible. The 1.3-point drop is within
run-to-run variation for 240 notes (one note is 0.4 points). The README score follows after
`scripts/28_ladder_vs_truth.py` and `35_readme_results.py`.

## Secrets, PHI and Claims Scan
Clean. Predicted status codes and probabilities per synthetic visit id.

## Findings
None blocking. Afterwards, the model card's scores should be checked against this file. Spec 020 wants the
card's numbers from the same run, and the publish step wrote them from it.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets / PHI / org claims | ✅ | |
| Simulated is labelled simulated | ✅ | real fine-tuning on synthetic notes |
| Idempotent writes | ✅ | Load results is keyed by file SHA-256; a new file hash is a new batch |

## Verdict
approve. Merge once CI is green.
