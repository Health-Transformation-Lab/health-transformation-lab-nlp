---
pr: 163
branch: feat/141-022-bench-schemas
title: "Name the schemas and Kaggle items for the three benches (spec 022)"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: read-only reviewer subagent (rubric, AGENTS.md, CLAUDE.md), findings verified by the coordinator
verdict: approve
---

# PR Review: Name the schemas and Kaggle items for the three benches (spec 022)

## Summary
Inside `health_transformation_lab`, the perio schemas become `<layer>_perio_bench` and access_bench and
oral_health_bench get empty bronze/silver/gold schemas; jobs, volume, model, notebooks, dashboards, Genie spaces,
docs and diagrams use the new names; the Kaggle notebooks, datasets, planned model and collection take
`perio-bench` names. Data is rebuilt, as in spec 021. Closes #141 and #142. Verdict: approve after the one
finding below was fixed in this PR.

## Scope of Change
- Areas touched: bundle (`databricks.yml`, `databricks/resources/*.yml`), notebooks, dashboards and Genie JSON
  (regenerated), Python package and tests, Kaggle scripts and workflows, docs, diagrams (regenerated and
  re-rendered), spec 022.
- Range reviewed: `origin/main...feat/141-022-bench-schemas`

## CI Status
| Check | Status |
|---|---|
| python, postgres, r-parity, bundle, azure-infra, check | success on the first head; 753 passed, 15 skipped locally after the fix |

## Secrets, PHI and Claims Scan
All clean. No credentials, no real data, no organization claims; the organization CLAUDE.md names does not
appear in the diff.

## Strengths
- Old schemas keep their bundle keys, so `prevent_destroy` can't fail the deploy and nothing is dropped.
- `test_no_legacy_schema_names.py` keeps the old suffix from creeping back.
- The kernel slugs now match the titles Kaggle derives them from.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
- **Legacy blocks were declared for uat, which never deployed** (`databricks.yml`, `test_bundle.py`, docs,
  spec). The deploy runs on main show uat stopping at "Stop if this environment isn't configured"; only dev
  deployed the spec 021 schemas (run at `a23e72d`). Declaring them in uat would have created empty old schemas
  on its first deploy. **Fixed:** legacy blocks are under dev only; `LEGACY_TARGETS = ("dev",)`; docs and spec
  say dev deployed them and uat and prod never did.

### 🔵 Nits / suggestions (Minor)
- No test checks that every `${resources.*}` reference resolves per target; CI's `bundle validate` covers it.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets, no PHI, no organization claims | ✅ | scans clean |
| Spec for big changes | ✅ | `specs/022-bench-schemas/` |
| Test first | ✅ | new tests written before the code |
| Configuration | ✅ | `legacy_domain` declared once; names in `schemas.py`; PR says all three targets change |
| Commits | ✅ | imperative subject, body says why, co-author trailer |

## Test Coverage
New: `test_schemas.py`, `test_no_legacy_schema_names.py`, bundle tests for the bench schemas, dev-only legacy
entries, jobs, volume and model; Kaggle slug and collection names. Full suite passes.

## Verdict
Approve.
