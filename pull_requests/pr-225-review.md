---
pr: 225
branch: kaggle-results/encoders-40762796130
title: "Add GPU encoder results from Kaggle (four encoders)"
author: github-actions[bot]
reviewed_at: 2026-10-28
reviewer: coordinator verification against the Kaggle kernel log (version 3)
verdict: approve
---

# PR Review: Add GPU encoder results from Kaggle (four encoders)

## Summary
The first full GPU run of the five encoders spec 002 left for a GPU
([run 3](https://github.com/healthtransformationlab/health-transformation-lab-nlp/actions/runs/40762796130), from
`main` at 3d9752a, 1 h 50 min on Kaggle's T4s with gradient checkpointing, #172). All five trained and saved
predictions. Four trained normally. `gatortron-base+lr2e-05` diverged, and its file is removed from this
PR. Approve the four.

## Scope of Change
- `data/datasets/ai_predictions_{modernbert-large,bioclinical-modernbert-large,longformer-base,clinical-longformer}.csv`:
  240 rows each
- `data/datasets/results_manifest.csv`: four rows, `source = kaggle`, with the run URL
- Commits:
  - 9206461 Add GPU encoder results from Kaggle (bot)
  - Leave out the diverged GatorTron run, and this review
- Range reviewed: `3d9752a..HEAD`

## What the run measured (synthetic notes; not evidence about real records)
| Encoder | Training loss, first log → last log | Exact status vs answer key | Classes predicted |
|---|---|---|---|
| modernbert-large | 2.82 → 0.15 | 82.5% | 6 |
| bioclinical-modernbert-large | 2.86 → 0.16 | 81.2% | 5 |
| longformer-base | 3.22 → 0.42 | 78.8% | 5 |
| clinical-longformer | 3.10 → 0.37 | 77.9% | 5 |
| gatortron-base+lr2e-05 (left out) | 3.68 → 32.3 (epoch 1.1) → 7.36 | 20.0% | 1 |

For comparison, the class-weighted ModernBERT-base on main scores 83.8%.

## Secrets, PHI and Claims Scan
Clean. The files hold predicted status codes per synthetic visit id, with no text.

## Findings
### 🔴 Blocking (Critical)
- **Fixed.** `ai_predictions_gatortron-base+lr2e-05.csv` came from a diverged run that answers one class for
  every note. Committing it would put a broken model on the leaderboard as a result. It is removed from this
  branch, with its manifest row. The cause and the rerun are #226.

### 🟡 Should fix (Important)
None.

### 🔵 Nits (Minor)
- The workflow token can't open PRs (Settings → Actions → General → "Allow GitHub Actions to create and
  approve pull requests"), so this one was opened by hand.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets / PHI / org claims | ✅ | |
| Simulated is labelled simulated | ✅ | real fine-tuning on synthetic notes; a failed run is not presented as a result |
| Idempotent writes | ✅ | Load results is keyed by file SHA-256 |

## Verdict
approve. Merge once CI is green.
