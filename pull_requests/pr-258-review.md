---
pr: 258
branch: fix/254-025-hf-token-shape
title: "Say which Hugging Face secret the publish check used, and why it's wrong"
author: jcbowyer
reviewed_at: 2026-10-29
reviewer: coordinator verification
verdict: approve
---

# PR Review: Say which Hugging Face secret the publish check used, and why it's wrong

## Summary
"Publish datasets" failed five times at its token check with a message that didn't say which secret it read or
what was wrong. This PR:
- passes the two secrets separately and names the one used;
- trims copy-and-paste whitespace and quotes;
- describes a bad value by its length and shape, never its characters.

Tests were written first. Approve.

## Scope of Change
- `.github/workflows/kaggle-publish.yml`: both Hugging Face steps get `HF_PUBLISH_TOKEN` and `HF_TOKEN`
  separately, and the check prints its source
- `huggingface/publish.py`: `clean_token`, `token_from_env`, `_shape`, and `check_token(source, env)`; uploads
  use the cleaned token
- `python/tests/test_hf_publish.py`: 10 new cases; the #249 test updated to the separate secrets
- Range reviewed: `origin/main..HEAD`

## Secrets, PHI and Claims Scan
Clean. The messages never include any characters of the value. Tests assert that the value, and any part of it,
is absent. GitHub masks the secrets in logs as before.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important)
None.

### 🔵 Nits (Minor)
- The Kaggle-key hint reveals only that the value is 32 lowercase hex characters, which is no more than its
  length and alphabet. That is acceptable for a masked, failed check.
- A valid-looking `hf_` token that Hugging Face refuses still raises from `whoami` as an HTTP error. That
  path is unchanged and already names the call.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets / PHI / org claims | ✅ | |
| Test first | ✅ | 10 failed before the code |
| Configuration and secrets | ✅ | the setting is checked before work, named, and never printed |
| Commits | ✅ | |

## Test Coverage
`cd python && pytest -q tests`: 1056 passed, 15 skipped.

## Verdict
approve. Merge once CI is green, then start a new "Publish datasets" run.
