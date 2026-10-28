---
pr: 181
branch: chore/180-renamed-org-links
title: "Point repo links at the renamed healthtransformationlab org"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve
---

# PR Review: Point repo links at the renamed healthtransformationlab org

## Summary
After #167 the org was renamed from `Health-Transformation-Lab` to `healthtransformationlab`, so the links #167 set
only worked through GitHub's redirect. This PR swaps the same files to the new address, rebuilds the platform diagram,
and widens the guard test to flag the previous org name too, ignoring case as GitHub does. The new address answers
(`git ls-remote` returns `main`'s head), the regex doesn't match it, and the tests pass. Approve.

## Scope of Change
- Files changed: 11 (+18 / -17, the PNG excluded)
- Areas touched: python (tests), kaggle, databricks (notebook), r (README), diagrams
- Commits: 57968e6 Point repo links at the renamed healthtransformationlab org
- Range reviewed: `40e5eed..57968e6`

## CI Status
| Check | Status |
|---|---|
| Check the branch name and issue link | ⏳ running at review time |
| Test every change (python, postgres, r-parity, bundle) | ⏳ running at review time |

## Secrets, PHI and Claims Scan
- Secrets: clean.
- PHI / real data: clean (no data files touched).
- Organization claims: clean (only repository URLs and a diagram label).

## Strengths
- The regex's `health-transformation-lab/` branch needs the hyphens, so it can't match the new
  `healthtransformationlab/` address. The reviewer checked it against the new address, other casings and the local
  clone path.
- The diagram builder re-run leaves no diff, so the committed `.drawio` and `.png` match what it generates.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
None.

### 🔵 Nits / suggestions (Minor)
1. Test first isn't visible in the history: the test change and the link swap share one commit. Verified separately:
   with only the test changes applied, `test_repo_links_name_the_org` and both Kaggle card tests failed (3 failed,
   17 passed) before the links were swapped.
2. Outside the diff: the reviewing session's local clone still has the old address as its remote; it works through
   the redirect and changes nothing in the repo.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | ✅ | Scan clean |
| Synthetic only, no PHI | ✅ | No data touched |
| No organization claims; vendors cited | ✅ | URLs only |
| Test first | ✅ | Failing run recorded above |
| Python and R in parity | ✅ | Only `r/README.md` |
| Simulated is labelled simulated | n/a | |
| Seeds fixed | n/a | |
| Paths | ✅ | Test uses `REPO_ROOT` |
| Spec for big changes | n/a | Link fix; issue #180 |
| Prices | n/a | |
| Commits | ✅ | Imperative subject, why in body, `Closes #180`, co-author trailer |
| Docs | ✅ | R README and walkthrough updated |
| Configuration | n/a | No settings change |
| Secrets register | n/a | |
| Idempotent writes | n/a | |
| Alerts | n/a | |

## Test Coverage
- `cd python && python -m pytest -q tests`: 762 passed, 15 skipped. `ruff check` on the changed tests: clean.
- Both notebooks parse as JSON. `git grep -i` finds neither old owner outside history.
- Not run: R parity (no R here); CI `r-parity` covers it.

## Verdict
**Approve.** Merge once CI is green on the head.
