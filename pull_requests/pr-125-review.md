---
pr: 125
branch: feat/114-018-gold-naming
title: "Name gold tables and columns by one SQL convention (spec 018)"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: independent reviewer subagent (read-only) + coordinator verification
verdict: approve-with-nits
---

# PR Review: Name gold tables and columns by one SQL convention (spec 018)

## Summary
The PR adds the "SQL and data names" conventions to AGENTS.md and renames the gold tables and columns to match them,
through one tested mapping (`gold_names.py`). It also moves the corpus judge to its own table and adds a migration
task ahead of Load results. The review found nothing Critical, but four Important problems, three of them in the
migration: it was untested, it would fail on an old `judgments` table the corpus judge wrote (stopping Load results on
every deploy), and it lost rows when a job wrote a new table first. All four were verified and fixed on the branch
(merge commit `d1df885`). The Databricks behaviour (migration, notebooks, dashboard queries) is reasoned, not run:
pyspark isn't available in the session. Verdict: approve-with-nits; run the migration once in dev and compare row
counts before dropping the old tables.

## Scope of Change
- Files changed: about 38 (+1.5k / -0.8k), most of them generated diagrams
- Areas touched: python / databricks / docs / specs / diagrams / AGENTS.md
- Commits: 8a5054a Name gold tables and columns by one SQL convention (spec 018); d1df885 Merge the gold diagram fixes;
  make the gold migration safe
- Range reviewed: `69cc917..8a5054a`, then the fix merge

## CI Status
| Check | Status |
|---|---|
| check (PR conventions) | pass |
| python | pass on 8a5054a |
| postgres | pass |
| r-parity | pass on 8a5054a |
| bundle | pass |
| azure-infra | pass |

## Secrets, PHI and Claims Scan
- Secrets: clean.
- PHI / real data: clean. No `data/` file changed; the CSV twins are untouched.
- Organization claims: clean. DE_Assessment is named only as a repository the conventions are adapted from.

## Strengths
- One mapping module, and `to_gold` fails on a column it doesn't know.
- The migration never drops a table; it prints the `DROP TABLE` statements instead.
- `fact_corpus_judge_call` ends the two judge jobs overwriting each other.
- Convention tests are tied to the declared model, so the ERDs, the docs and the writers agree.
- The plan says which environments change.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important): fixed
1. **The migration failed on a corpus-shaped `judgments` table.** If `02_llm_judge.sql` wrote `judgments` last, its
   columns (`method`, `pred`, `supported_status`, …) had no mapping under `fact_judge_call`. The migrate task would
   raise, and `load` (which depends on it) would fail on every deploy.
   - Verified: `RENAMED["judgments"]`, together with the unknown-column check.
   - **Fixed:** `migration_plan` routes `judgments` by its columns, to `fact_judge_call` or `fact_corpus_judge_call`.
     Tested in `test_judgments_written_by_the_corpus_judge_go_to_the_corpus_table`.
2. **"Skip once the new table exists" lost rows.** If the MedGemma reader or the judge scorecard ran before the
   migration, it created the new table, and the old rows were never copied.
   - Worse, `dim_result_file` had been migrated, so Load results considered those files already loaded.
   - **Fixed:** when the new table already exists, the old rows whose batch key it lacks are merged in
     (`MERGE_KEYS`, null-safe anti-join). Summary tables rebuilt since are left as stale.
   - The scorecard now refuses to run while its old calls are unmigrated, so it never pays for them twice.
3. **No test ran the migration logic.** **Fixed:** the decision is now a pure function, `gold_names.migration_plan`.
   Eight tests cover copy, merge, stale, rewrite, the two `judgments` shapes, an unknown column and the "nothing to
   do" case, plus a check that every `MERGE_KEYS` entry is made of declared gold columns.
4. **The dashboard column test was too lenient.** It removed every `AS` alias from the names it checked, so a query
   reading an old column under its old name (`difference AS difference`) still passed.
   - Reproduced by the reviewer with a mutation.
   - **Fixed:** only the alias after each `AS` is removed, and a new test asserts the same mutation is caught.

### 🔵 Nits / suggestions (Minor)
5. `localCheckpoint()` might not work on serverless. Removed; Delta overwrites from the snapshot it read. **Fixed.**
6. The bigint cast could turn values into nulls without an error. The migration now compares null counts before
   and after the cast and fails on a difference; copies and rewrites also check row counts. **Fixed.**
7. The `delta.py` docstring still used the old names. **Fixed.**
8. AGENTS.md disagreed with this PR's own code. **Fixed:**
   - "lowercase keywords": the rule now says keywords are lowercase in new SQL, with one case per file.
   - The batch-key line now names `run_id`/`run_ts` or `file_sha256`/`loaded_ts`, plus `git_commit_sha`.
   - The list of objects not yet converted now includes `encoder_gpu_predictions`.
9. The summary-prefix test hard-coded `judge_` and `deid_`. It now checks `<subject>_<noun>`, as AGENTS.md says.
   **Fixed.**
10. Two guards for old tables in `10_load_results.py` were removed (the `{"source","sha256"}` column check). Every
    writer in git history added those columns, so this is noted, not changed.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | yes | |
| Synthetic only, no PHI | yes | |
| No organization claims; vendors cited | yes | |
| Test first | yes | tests written and seen failing before `gold_names.py` and `migration_plan` |
| Python and R in parity | n/a | CSVs R reads unchanged; r-parity green |
| Simulated is labelled simulated | yes | `is_simulated` |
| Spec for big changes | yes | `specs/018-gold-naming/` (spec, plan, tasks) |
| Commits | yes | |
| Docs | yes | gold_tables, results_storage, deployment, operations updated |
| Configuration | yes | no new settings; the plan says dev migrates on merge, uat and prod on their next deploy |
| Idempotent writes | yes | copy/rewrite are overwrites; merge adds only rows whose batch key is absent |

## Test Coverage
Covered: the mapping for every CSV twin and loader frame, every `llm_details_*.csv`, unknown-column failures,
integer counts, the `from_gold` round trip, the convention rules, the dashboard columns (with a mutation test),
`migration_plan` case by case, and the job and notebook wiring.

Run locally: `cd python && pytest -q tests`, 683 passed, 14 skipped; ruff is clean on the new Python files.

Not covered: the Spark side of the migration (renames, the anti-join, casts). It runs only on Databricks.

## Verdict
approve-with-nits. Before dropping the old tables, run Load results once in dev and compare the old and new row
counts the migration prints.
