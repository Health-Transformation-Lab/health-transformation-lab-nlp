---
pr: 83
branch: claude/databricks-token-pr-merge-xjbpfa
title: "Kaggle: MedGemma from Kaggle Models, runs pinned to the workflow's commit, and the GPU encoders on Kaggle"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator (workflow fix with regression tests)
verdict: approve
---

# PR Review: Kaggle MedGemma from Kaggle Models, pinned commits, GPU encoders on Kaggle

## Summary
Closes #82 and #84. This PR has three parts:

1. It merges `claude/festive-darwin-er45u9` (e1455e4). MedGemma 1.5 4B now comes from Kaggle Models as a Keras preset and is converted on Kaggle, so a pushed notebook needs no Hugging Face token. A 10-note test passed from that branch (run 40688922023, gate pass 100%).
2. The notebook now runs the commit the workflow was started from. The `branch` input defaults to the branch picked under "Use workflow from", and the workflow passes `github.sha` as `COMMIT`. The notebook fetches and checks out that commit, then logs `code: <branch> @ <sha>`. If you type in a different branch, it still runs that branch's latest commit.
3. It adds the GPU encoders of spec 002 T017 on Kaggle: `kaggle-encoders.yml` and `kaggle/encoder_gpu.ipynb`. Rungs and learning rates default to the Databricks job's `databricks.yml` variables, and a test keeps the workflow inputs equal to them. Each rung's predictions are saved as soon as it finishes; a failed rung is skipped, and the notebook fails at the end. A full run opens a results PR (spec 016).

## Findings
None blocking.

- 🔵 Kaggle's own pip warning (`keras-nlp 0.26.0 requires keras-hub==0.26.0`) appears in the log. The run still converts and reads the model correctly. This predates this PR's second commit.
- Risk: the encoder notebook hasn't run on Kaggle. Possible problems are ModernBERT on a T4 without flash attention (transformers falls back to SDPA) and the time five large models take; a 10-note test (1 epoch) settles both. If a full run passes the 330-minute wait, `collect_only` picks it up.
- 🔵 The two workflows duplicate their credential, wait and PR steps (about 60 lines). That was kept deliberately rather than moving the working MedGemma workflow into a shared action; the tests check both copies.
- Risk: if the pinned branch is deleted, re-running an old Kaggle notebook version by hand fails at clone. That is acceptable, because each workflow run pushes a fresh notebook.

## Checks
- `pytest -q tests`: 602 passed, 14 skipped. 13 new tests, written first; they failed before the code existed.
- Ran the encoder notebook's loop locally with `tfidf_logreg` plus a made-up rung name: it saved one, skipped one, then raised. `record_results.py` then refused the 10-row file (exit 3).
- Shallow clone, then `fetch --depth 1 origin <sha>` and `checkout FETCH_HEAD`, run against github.com: checks out e1455e4.
- `ruff check` on the changed Python files: clean (the old `re.M` is now `re.MULTILINE`).
- Scans: no secrets or tokens in the diff, no PHI (synthetic notes only), no organization claims. The MedGemma terms are cited as Health AI Developer Foundations.

## Compliance
| Rule | Result |
|---|---|
| No secrets, synthetic only, no org claims | Pass |
| Test first | Pass |
| Configuration | Pass (one workflow input, documented in its description; no new credential) |
| Secrets register | Kaggle token entry lists both workflows; no Hugging Face token is needed on Kaggle |
| Spec | spec 002 T017 notes the Kaggle alternative (no new dataset, metric or label rule) |
| Branches and issues | Pass (`claude/*` branch, `Closes #82`, `Closes #84`) |
