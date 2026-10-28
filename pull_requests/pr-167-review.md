---
pr: 167
branch: chore/166-repo-org-links
title: "Point repo links at the Health-Transformation-Lab org"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve-with-nits
---

# PR Review: Point repo links at the Health-Transformation-Lab org

## Summary
The repo moved from `jcbowyer` to the `Health-Transformation-Lab` org. This PR points every current link at the
new address: the Kaggle notebooks' `git clone`, the Kaggle dataset cards and their test, the walkthrough notebook,
the R README and the platform diagram (source regenerated, PNG re-rendered). It adds a test that fails if a current
file links to the old owner again. The new URL matches the remote exactly, nothing outside history still names the
old owner, and the tests pass. Approve with nits: the two nits fixed here are cosmetic, and the others stay by choice.

## Scope of Change
- Files changed: 11 (+32 / -14, the PNG excluded)
- Areas touched: python (tests), kaggle, databricks (notebook), r (README), diagrams
- Commits:
  - 3a03369 Point repo links at the Health-Transformation-Lab org
  - 4537139 Merge remote-tracking branch 'origin/main' into chore/166-repo-org-links
  - (this review's commit: wrap the new test's long lines, add this review)
- Range reviewed: `33899f3..4537139` (merge base to head, the merge of `main` excluded from findings)

## CI Status
| Check | Status |
|---|---|
| Check the branch name and issue link | ✅ success |
| Test every change (python, postgres, r-parity, bundle) | ⏳ in progress at review time |

## Secrets, PHI and Claims Scan
- Secrets: clean (no keys, tokens, passwords or credentialed URLs in the diff).
- PHI / real data: clean (no data files touched).
- Organization claims: clean (only repository URLs and a diagram label change).

## Strengths
- The guard test uses the same `HISTORY` exclusions as `test_no_old_names_left`, so past run links in
  `data/datasets/results_manifest.csv`, reviews and specs keep the address they had.
- The `jcbowyer/DE_Assessment` credits are correctly left alone (a different repo), and the regex doesn't match them.
- The diagram was rebuilt with the repo's own tools (`build_drawio.py`, then draw.io's export page per
  `diagrams/_build/render.md`); only the label changed, and the PNG keeps its size.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
None.

### 🔵 Nits / suggestions (Minor)
1. `python/tests/test_rename.py`: the skip condition and docstring ran past the 100-character line length
   (`python/pyproject.toml`); ruff doesn't enforce E501, so measured with `awk`. **Fixed** on the branch: split the
   condition and rewrapped the docstring. The `subprocess.run` line (101) is copied exactly from the existing test
   and stays.
2. `python/tests/test_rename.py`: the `specs/0` prefix in `HISTORY` also skips current specs. Kept: it is the
   existing test's definition of history, and the two tests should agree.
3. The old-owner regex is case-sensitive. Kept: no other spelling exists (`git grep -nIi jcbowyer` finds only the
   `DE_Assessment` credits).

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | ✅ | Scan clean |
| Synthetic only, no PHI | ✅ | No data touched |
| No organization claims; vendors cited | ✅ | URLs only |
| Test first | ✅ | `test_repo_links_name_the_org` and both Kaggle card tests failed before the fix |
| Python and R in parity | ✅ | Only `r/README.md`; no labels, scoring, reliability or cost-effectiveness change |
| Simulated is labelled simulated | n/a | |
| Seeds fixed | n/a | |
| Paths | ✅ | Test uses `REPO_ROOT` from `paths` |
| Spec for big changes | n/a | A link fix; issue #166 |
| Prices | n/a | |
| Commits | ✅ | Imperative subject, body says why, `Closes #166`, co-author trailer |
| Docs | ✅ | R README and walkthrough updated |
| Configuration | n/a | No settings change; no environment changes |
| Secrets register | n/a | No credential touched |
| Idempotent writes | n/a | |
| Alerts | n/a | |

## Test Coverage
- New: `test_repo_links_name_the_org` covers every tracked text file outside history.
- Run locally: `cd python && python -m pytest -q tests`, 756 passed, 15 skipped (after merging `main`);
  `tests/test_rename.py` 3 passed after the nit fix; `ruff check tests/test_rename.py` clean. The one ruff I001 on
  `diagrams/_build/build_drawio.py:7` is also on `main` and isn't from this PR.
- Both notebooks still parse as JSON; re-running `build_drawio.py` on the merged tree gives no further diff.
- Not run: R parity (no R here); CI `r-parity` covers it.

## Verdict
**Approve with nits.** Nothing blocks. Merge once CI is green on the head.
