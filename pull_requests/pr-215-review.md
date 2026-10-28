---
pr: 215
branch: fix/214-004-llm-revision-gold-name
title: "Give the reader's revision column a gold name"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator verification
verdict: approve
---

# PR Review: Give the reader's revision column a gold name

## Summary
The MedGemma 4B v1 results PR (#210) failed `python`: its `llm_details` file has the reader's new `revision`
column, and `fact_llm_call` doesn't declare it. This PR maps it to `model_revision_id` in `gold_names.py` and
the gold model, regenerates the ERD sources, and keeps older reader files valid. The test was written first,
and it failed before the fix. Approve.

## Scope of Change
- Files: `gold_names.py` (+1), `gold_model.py` (+1), `test_gold_names.py`, the regenerated
  `diagrams/gold/data_model.md` and `.drawio`/`.mmd` sources, this review
- Commits: f24bbb8 Give the reader's revision column a gold name; Review PR #215
- Range reviewed: `b3b8f83..HEAD`

## CI Status
| Check | Status |
|---|---|
| python, postgres, bundle, check | see the PR |

## Secrets, PHI and Claims Scan
Clean.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important)
None.

### 🔵 Nits (Minor)
- The ERD PNGs are not re-rendered: that needs draw.io's export page (`diagrams/_build/render.md`). The
  `.drawio`, `.mmd` and `data_model.md` sources are current.
- `_id` fits "an identifier from a source" (AGENTS.md), and both a Kaggle handle and a commit SHA are that.
  `_sha` would be wrong for the Kaggle handle.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets / PHI / org claims | ✅ | |
| Test first | ✅ | `test_the_readers_revision_column_has_a_gold_name` failed before the fix |
| SQL and data names | ✅ | `model_revision_id`, declared in gold_names and gold_model; `test_sql_conventions` passes |
| Idempotent writes | ✅ | unchanged; `mergeSchema` adds the column |
| Configuration | ✅ | no settings; the PR says which environments get the column |
| Commits | ✅ | |

## Test Coverage
`cd python && pytest -q tests`: 836 passed, 15 skipped. With #210's file copied in, `test_gold_names`,
`test_gold_model` and `test_sql_conventions` pass.

## Verdict
approve. Merge once CI is green, then #210.
