---
pr: 108
branch: feat/104-018-lab-grader
title: "Lab grader on Databricks: tables with a seeded simulated sample, a dashboard and a Genie space"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator review (the same builder and checks as PR #107, whose subagent review covered the shared code)
verdict: approve-with-nits
---

# PR Review: Lab grader on Databricks

## Summary
Spec 018 US3, US4 and the lab half of US5, stacked on #107.
- **Tables:** `grader_questions` and `grader_answers`. A seeded SIMULATED sample fills them until a real run.
- **Dashboard:** the Lab grader, designed from the pitch's uplift and leaderboard slides with GlobalDentBench's
  practices.
- **Genie space:** it defines each measure as the dashboard does.

Every query runs in tests, and the uplift matches pandas. Approve with nits; the deploy checks are the same as
for #107.

## Scope of Change
- Files changed: 16 (two sample CSVs, generated dashboard and space, modules, script, tests, docs, spec)
- Commits: ae7f064 Lab grader on Databricks
- Range reviewed: `origin/feat/102-018-dq-grader..HEAD`

## CI Status
| Check | Status |
|---|---|
| python | pending; 676 passed, 14 skipped locally |

## Secrets, PHI and Claims Scan
All three are clean.
- The sample is made up, and says so on every row.
- The `sim:` model names are not real products.
- No organization or company result is claimed. The GlobalDentBench sentence on cost is cited.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
- **To confirm on deploy:** the scatter widget (version 3) has no example in the repo; check it on the first dev
  deploy with #107's widgets.

### 🔵 Nits / suggestions (Minor)
- **The uplift interval** treats the two answer sets as independent, though they answer the same questions.
  Pairing would narrow it, so this is conservative, and the table description says so.
- **`answers_each`** shows as a decimal in DuckDB (75.0). Databricks returns a whole number from `SUM` of
  integers, so there is nothing to change.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| Simulated labelled | ✅ | `simulated_*` files, `sim:` models and judge, `simulated = true` on every row, SIMULATED banner and Genie instruction |
| Seeds fixed | ✅ | `--seed`, default 2026; reproducibility tested |
| Test first | ✅ | the table and dashboard tests failed before the code |
| Idempotent writes | ✅ | overwrite per table, with `sha256` |
| Telemetry | ✅ | `@traced` on every public function |
| Python and R parity | n/a | no study label, score or reliability change |

## Test Coverage
- **Sample:** its shape and seed, and that no model judges itself.
- **Real files:** `lab_tables` uses committed `grader_*.csv` over the sample.
- **Dashboard:** every lab query runs; the uplift matches pandas and sits inside its interval; ranks only within
  a category; the safety and level rows are right.
- **Genie space:** it reads the grader tables only and says simulated.

## Verdict
Approve with nits. Merge #107 first, then confirm the widgets and Genie spaces on the first dev deploy.
