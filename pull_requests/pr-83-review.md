---
pr: 83
branch: claude/databricks-token-pr-merge-xjbpfa
title: "Kaggle MedGemma: load from Kaggle Models (no HF token), and run the commit the workflow started from"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator (workflow fix with regression tests)
verdict: approve
---

# PR Review: Kaggle MedGemma from Kaggle Models, pinned to the workflow's commit

## Summary
Closes #82. This PR has two parts:

1. It merges `claude/festive-darwin-er45u9` (e1455e4). MedGemma 1.5 4B now comes from Kaggle Models as a Keras preset and is converted on Kaggle, so a pushed notebook needs no Hugging Face token. A 10-note test passed from that branch (run 40688922023, gate pass 100%).
2. The notebook now runs the commit the workflow was started from. The `branch` input defaults to the branch picked under "Use workflow from", and the workflow passes `github.sha` as `COMMIT`. The notebook fetches and checks out that commit, then logs `code: <branch> @ <sha>`. If you type in a different branch, it still runs that branch's latest commit.

## Findings
None blocking.

- 🔵 Kaggle's own pip warning (`keras-nlp 0.26.0 requires keras-hub==0.26.0`) appears in the log. The run still converts and reads the model correctly. This predates this PR's second commit.
- Risk: if the pinned branch is deleted, re-running an old Kaggle notebook version by hand fails at clone. That is acceptable, because each workflow run pushes a fresh notebook.

## Checks
- `pytest -q tests`: 593 passed, 14 skipped. Four new tests failed before the change.
- Shallow clone, then `fetch --depth 1 origin <sha>` and `checkout FETCH_HEAD`, run against github.com: checks out e1455e4.
- `ruff check kaggle/prepare_kernel.py`: one existing FURB167 (`re.M`). It is not on a changed line, and CI doesn't run ruff.
- Scans: no secrets or tokens in the diff, no PHI (synthetic notes only), no organization claims. The MedGemma terms are cited as Health AI Developer Foundations.

## Compliance
| Rule | Result |
|---|---|
| No secrets, synthetic only, no org claims | Pass |
| Test first | Pass |
| Configuration | Pass (one workflow input, documented in its description; no new credential) |
| Secrets register | Unchanged (no Hugging Face token is needed on Kaggle now) |
| Branches and issues | Pass (`claude/*` branch, `Closes #82`) |
