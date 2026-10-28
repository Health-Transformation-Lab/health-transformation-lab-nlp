---
pr: 232
branch: fix/228-018-migrate-legacy-schemas
title: "Carry rows left in the old gold schemas into gold_perio_bench"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve-with-nits
---

# PR Review: Carry rows left in the old gold schemas into gold_perio_bench

## Summary
The gold-name migration only looked in `health_transformation_lab.gold_perio_bench`. It printed "nothing to do" on
every dev run while the MedGemma reader's Databricks-only rows sat in the old catalog's gold schema (#228). The PR
adds `gold_names.legacy_plan` / `legacy_schemas` (tested) and a notebook step that merges each batch-keyed legacy
table by `MERGE_KEYS`, checks that every old key arrived, and prints `DROP TABLE` only for the checked tables. The
reviewer's one Important finding was fixed in 83d83a5: a DROP was listed for stale tables that were never
checked. The rest are minor. The notebook logic is sound by trace but has not run on Databricks yet; the first
Load results after merge is that run. Approve with nits.

## Scope of Change
- Files changed: 9 (+~200 / -12)
- Areas touched: python, databricks, docs
- Commits: the carry commit; fcf190b merge of main; 83d83a5 Print DROP only for legacy tables whose rows were checked
- Range reviewed: `origin/main...83d83a5`

## CI Status
| Check | Status |
|---|---|
| Test every change (Python, R parity, bundle) | success on fcf190b; re-running on 83d83a5 |
| Check the branch name and issue link | success |

## Secrets, PHI and Claims Scan
Clean: no credentials, no real data, no organization claims. Only table and schema names, plus synthetic row counts.

## Strengths
- The decision is a pure function with tests for copy, merge, stale, fail and unknown tables, like `migration_plan`.
- A key column the current table lacks (`run_id` before any reader run) is matched as null. So the repo rows don't
  duplicate and the reader rows do arrive; `not_carried` re-reads after `mergeSchema`.
- Per-table re-planning against the live `current` map stops two legacy tables with one target from overwriting
  each other.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
- ~~`11_migrate_gold_names.py`: `DROP` printed for stale tables never compared~~. **Fixed in 83d83a5:** stale tables
  print counts and "compare before dropping", with no DROP. A test checks the `continue` precedes `drops.append`.

### 🔵 Nits / suggestions (Minor)
- Every table in a legacy schema was read before filtering. **Fixed in 83d83a5:** only tables in `RENAMED` / `TABLES` are read.
- `databricks.yml` `legacy_gold_schemas` default repeats the catalog and `legacy_domain` suffix as a literal.
  Kept: a bundle variable default can't reference another variable, and the setting is declared once. Clear it when
  the old schemas are dropped (docs/deployment.md).
- The notebook widget default is empty, so a manual run reads no legacy schema. It now prints that.
- `merge_missing` / `not_carried` are notebook code, checked by trace and by string tests only. The first dev run's
  output confirms them before the printed DROPs are used.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | ✅ | |
| Synthetic only, no PHI | ✅ | |
| No organization claims | ✅ | |
| Test first | ✅ | 9 tests written failing first |
| Python and R in parity | n/a | no label, scoring, reliability or cost change |
| Simulated labelled | n/a | |
| Spec for big changes | ✅ | a bug fix under spec 018 with its issue (#228) |
| Configuration | ✅ | one bundle variable; parsed before work; dev changes, uat/prod skip (schemas missing) |
| Idempotent writes | ✅ | merge by batch key; a rerun adds nothing |
| Commits | ✅ | |

## Test Coverage
`cd python && pytest -q tests`: 943 passed, 15 skipped. ruff clean on the changed files (the notebook's import-order
note is on main too). Not run: the notebook on Databricks (it runs as Load results' first task after the merge deploy).

## Verdict
approve-with-nits. Merge when CI is green. Then read the `migrate_gold_names` output of the next Load results run
before running any printed DROP.
