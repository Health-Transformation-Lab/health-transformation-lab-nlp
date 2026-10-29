---
pr: 231
branch: fix/230-004-check-hf-token-first
title: "Check the Hugging Face token before the MedGemma reader does any work"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator verification
verdict: approve
---

# PR Review: Check the Hugging Face token before the MedGemma reader does any work

## Summary
The reader job's run with limit 0 (Databricks run 33428839369904) failed on a refused Hugging Face token (401),
but only when the weights loaded. By then it had started the GPU and built the study, and its retry started
over. `check_hf_access` makes one authenticated call first and fails at once with the reason and the fix. The
notebook calls it before any work. Approve.

## Scope of Change
- `python/health_transformation_lab_nlp/llm_reader.py`: `check_hf_access`, `@traced`
- `databricks/notebooks/03_medgemma_reader.py`: the check after reading the secret, for gated rungs
- `ops/secrets_register.yaml`: where the job stops when the token expires
- `python/tests/test_llm_reader.py`: six tests, written first
- Range reviewed: `b2e9434..HEAD`

## Secrets, PHI and Claims Scan
Clean. No token anywhere. The error message names the variable and the secret key, never the value (a test
checks this).

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important)
None.

### 🔵 Nits (Minor)
- The register's `stored_in` still mentions a Kaggle notebook secret `HF_TOKEN`. The Kaggle notebook reads
  Kaggle Models now and needs no token. That's for the owner's next register update.
- The job's retry policy still retries a refused token once. Databricks can't retry on some errors and not
  others, but the retry now fails in the first cell, so it costs seconds.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets / PHI / org claims | ✅ | |
| Test first | ✅ | 4 of the new tests failed before the code |
| Configuration and secrets | ✅ | credential checked with one cheap call before work; register updated |
| Telemetry | ✅ | `@traced` on the new public function |
| Commits | ✅ | |

## Test Coverage
`cd python && pytest -q tests`: 865 passed, 15 skipped. Not run against Hugging Face itself: the token in the
scope is the one being replaced.

## Verdict
approve. Merge once CI is green. The reader job still needs a new token in the secret scope.
