---
pr: 195
branch: docs/194-013-cite-patel-2026
title: "Cite Patel et al. 2026 and say what the status classifier could adopt"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator verification against PubMed and the PMC full text
verdict: approve
---

# PR Review: Cite Patel et al. 2026 and say what the status classifier could adopt

## Summary
This PR adds reference 53, Patel et al. 2026 (JDR Clin Trans Res), the follow-up to the 2022 model that spec
013 G10 is built on. Spec 013 G10 and G11 now name it, list what G10 could adopt, and hand the medical-record
side to spec 023. A test, written first, pins the entry and the spec rows. Every bibliographic fact and figure
was checked against PubMed (efetch, PMID 41673528) and the PMC full text (PMC13292087). Approve.

## Scope of Change
- Files changed: 3 (+53 / -2)
- Areas touched: docs, specs, python tests
- Commits: 88707df Cite Patel et al. 2026 and say what the status classifier could adopt
- Range reviewed: `9fb62e1..88707df`

## CI Status
| Check | Status |
|---|---|
| python, postgres, bundle, azure-infra, check (pr-conventions) | ✅ on 88707df |
| r-parity | skipped (no change can reach it) |

## Verified against the sources
| Claim | Source | OK |
|---|---|---|
| Authors Patel JS, Tellez M, Katiyar R, Al-Hebshi NN, Santana R, Yucel RM, Ismail A | PubMed AuthorList | ✅ |
| 2026;11(4):555–570, epub 2026-02-11 | PubMed Journal, Pagination, ArticleDate | ✅ |
| doi:10.1177/23800844251408849, PMC13292087 | PubMed ArticleIdList | ✅ |
| 20,946 adults; XGBoost among four models; 4 classes (healthy, I, II, III+IV) | abstract; Methods "Target variable" | ✅ |
| 70/30 split, stratified | Methods: "70% training and 30% testing sets, using stratified sampling" | ✅ |
| Brier score; PROBAST and TRIPOD-AI | Table 2; Methods and supplementary checklists | ✅ |
| Exp. 1 averages 66/86/84 (dental) and 66/86/86 (with medical); exp. 5 43/70/57 | Table 2 "Average" column | ✅ |
| 106 (abstract) vs 109 (Methods) features | abstract; "The final dataset included 109 independent variables" | ✅ |
| Abstract's 67/85/84 matches neither exp. 1 row | abstract vs Table 2 | ✅ |

## Secrets, PHI and Claims Scan
Clean. No credentials or data. Only published, cited figures, and the entry says the paper's data never comes
in. The paper is described as its authors describe it, with no organisation's plan or study implied.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
None.

### 🔵 Nits / suggestions (Minor)
- The issue said PubMed and PMC "weren't reachable" in the earlier session. Here they were, so the entry says
  what was checked instead.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets / PHI / org claims | ✅ | |
| Test first | ✅ | `test_patel_2026_citation.py` failed 3/3 before the edits |
| Python and R in parity | n/a | |
| Spec for big changes | ✅ | spec 013 updated; the medical-record work is spec 023 |
| Commits / Docs | ✅ | |
| Other rows | n/a | |

## Test Coverage
`cd python && pytest -q tests`: 835 passed, 15 skipped. `ruff check` on the new test: clean.

## Verdict
approve. Merge.
