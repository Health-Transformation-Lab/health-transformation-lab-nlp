---
pr: 173
branch: fix/172-encoder-grad-checkpoint
title: "Train the large encoders with gradient checkpointing on Kaggle's T4"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator review after merge (recorded under #176)
verdict: approve
---

# PR Review: Train the large encoders with gradient checkpointing on Kaggle's T4

## Summary
`HFEncoder` takes `grad_checkpoint`. `11_ai_predict.py --grad-checkpoint` turns it on, and the Kaggle encoder notebook
passes it. Before, four of five encoders ran out of memory on the T4 (`CUDA out of memory`, batch 16 x 256 tokens).
Checkpointing recomputes activations instead of storing them, so batch size, learning rate, epochs, seed and the
output file name are unchanged (tested). Databricks' A10 job doesn't use it. Approve.

## Scope of Change
- Files: `rungs.py`, `11_ai_predict.py`, `kaggle/encoder_gpu.ipynb`, `test_rungs_checkpoint.py`,
  `test_kaggle_encoders.py` (+55 / -11)
- Commit: `9fc03ed`; merged as `f57a4be`

## CI Status
| Check | Status |
|---|---|
| python, postgres, r-parity, bundle, azure-infra, check | success on `9fc03ed` |
| Kaggle encoders workflow (`run`), from the branch, 10-note test | success: all five encoders saved, none failed |

## Secrets, PHI and Claims Scan
Clean.

## Findings
None. Note: checkpointing slows training by about a third. A full Kaggle run (240 notes, 3 epochs) takes longer than
before, which only matters against Kaggle's weekly GPU quota.

## Repo-Rule Compliance
Test first (three new tests failed before the change), no metric or label change, so R not affected, no settings
change. `training_kwargs` is `@traced`.

## Verdict
**approve.**
