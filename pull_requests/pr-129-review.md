---
pr: 129
branch: claude/remove-carequest-references
title: "Remove named-organization references from disclaimers and docs"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator (docs-only, 4 files; no subagent needed)
verdict: approve
---

# PR Review: Remove named-organization references from disclaimers and docs

## Summary
This PR removes every mention of CareQuest from the repo (closes #128). The README and DISCLAIMER
not-affiliated lines no longer name an organization; `docs/radiograph.md` drops the ACCELERATE/Overjet
pilot bullet and names only Overjet in its disclaimer; `docs/references.md` drops reference 20. No code
changes. Verdict: approve.

## Scope of Change
- Files changed: 5 (4 docs, plus this review)
- Areas touched: docs, pull_requests
- Range reviewed: `origin/main..HEAD`

## CI Status
| Check | Status |
|---|---|
| python, postgres, r-parity, bundle | pending; no code, data or bundle files touched |

## Secrets, PHI and Claims Scan
All three are clean. The change removes an organization reference; it adds no claims. The remaining
Overjet statements are cited to Overjet's own pages.

## Strengths
- Reference 20 is removed without renumbering, so citations by number elsewhere (e.g. 37–45 in
  `docs/deidentification.md`) stay correct.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
None.

### 🔵 Nits / suggestions (Minor)
- Reference list now has a gap at 20. Intended (numbers are stable IDs); no action.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets, no PHI, no organization claims | ✅ | scans clean |
| Vendors cited | ✅ | Overjet facts keep their citations |
| Commits | ✅ | imperative subject, body says why, co-author trailer |
| Docs | ✅ | README length unchanged |

## Test Coverage
Docs only. No test reads these files (`grep` over `python/tests`, `r/tests` and `.github`).

## Verdict
Approve.
