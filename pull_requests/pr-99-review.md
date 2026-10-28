---
pr: 99
branch: docs/97-004-keras-vs-hf-decision
title: "Record the KerasHub vs converted-HF comparison and keep the HF backend"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator (docs-only, 4 lines; no subagent needed)
verdict: approve
---

# PR Review: Record the KerasHub vs converted-HF comparison and keep the HF backend

## Summary
This PR adds task T020 to spec 004. It records a 10-note Kaggle comparison of a KerasHub backend with the
converted-HF path already on `main`, and the decision to keep only the HF path. The note says it covers
ten notes only and is not a result. No code changes. Verdict: approve.

## Scope of Change
- Files changed: 1 (+4 / -0)
- Areas touched: specs
- Commits:
  - 6429f0a Record the KerasHub vs converted-HF comparison and keep the HF backend
- Range reviewed: `origin/main..6429f0a`

## CI Status
| Check | Status |
|---|---|
| python | pending; 616 passed, 14 skipped locally |
| postgres, r-parity, bundle | pending; untouched by this change |

## Secrets, PHI and Claims Scan
All three are clean. The figures come from synthetic notes.

## Strengths
- The decision is recorded next to the evidence for it, so the Keras branch can be deleted safely.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
None.

### 🔵 Nits / suggestions (Minor)
None.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets, no PHI, no organization claims | ✅ | scans clean |
| Simulated labelled | ✅ | a real 10-note run, labelled as too small to count as a result |
| Spec for big changes | ✅ | this PR is the spec update |

## Test Coverage
Docs only. The full suite was run locally and passed.

## Verdict
Approve.
