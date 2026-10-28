---
pr: 107
branch: feat/102-018-dq-grader
title: "EHR DQ grader on Databricks: dq tables, an AI/BI dashboard and a Genie space"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve-with-nits
---

# PR Review: EHR DQ grader on Databricks

## Summary
Spec 018 US1, US2 and the DQ half of US5.
- **Tables:** the data-quality CSVs become eight `dq_*` gold tables, overwritten on every Load results run.
- **Dashboard:** the EHR DQ grader is a lighter version of the Perio DQ Monitor design.
- **Genie space:** it reads the same tables and defines each measure exactly as the dashboard computes it.

The reviewer recomputed the measures from the CSVs:
- The accuracy measure compares the same six labels on both sides.
- The transition direction matches `transitions_by_method.better`: 168 of 1,230 = 0.1366.
- The Spark write follows the existing loader's pattern.

No critical findings. One important finding (the Genie space's format) is fixed. What remains needs a dev deploy
to confirm, so the verdict is approve-with-nits.

## Scope of Change
- Files changed: about 19 (spec, two modules, a build script, two test files, the generated dashboard and space,
  bundle resources, notebook, workflows, docs)
- Areas touched: python, databricks, specs, docs, ci
- Commits:
  - 13ce026 EHR DQ grader on Databricks
  - one commit with the review fixes and this file
- Range reviewed: `origin/main..HEAD`

## CI Status
| Check | Status |
|---|---|
| python | pending; 665 passed, 14 skipped locally |
| bundle | pending; validate now runs with the direct engine on CLI 1.3.0 |

## Secrets, PHI and Claims Scan
All three are clean. `dq_visits` holds statuses only, never note text, and a test checks it.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
- **Fixed: the Genie space's format.** It had eight `text_instructions` entries; Genie keeps one general
  instruction, and exported spaces list their sample questions sorted by id. The space now has one instruction
  (the eight paragraphs joined) and sorted questions, and a test checks both.
- **To confirm on deploy:**
  - that `"version": 2` with `file_path` loads on CLI 1.3.0;
  - that the counter, bar and heatmap widget specs render. Nothing local checks either.

### 🔵 Nits / suggestions (Minor)
Fixed:
- **Temporal wording:** the denominator is visit pairs 1–2 years apart with no treatment between (`pairs`), not
  later visits. The tile and the Genie instructions say so.
- **Check statuses:** the text tile claimed statuses the table doesn't hold. It is replaced by a counter for
  accuracy in the design order (`accuracy_design_pct` was computed but never shown), and the checks table
  explains PASS and REPORT.
- **Heatmap note:** it no longer depends on which way the y axis is drawn.
- **Clinic filter:** it offered "All", which empties the accuracy and prevalence charts. The filter now applies
  only to those two; the checks table shows every clinic and All.

Left as is:
- **Missing `proc_dx_completed` row:** `completeness_columns.csv` has no row for it, though the completeness tile
  uses it. Its missing share equals the planned codes' (29.5%), which the bar's description now says. Adding the
  row means changing `20_data_quality.py` (spec 005), which is out of scope.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets, PHI or organization claims | ✅ | |
| Test first | ✅ | every module and the notebook wiring have tests written first |
| Idempotent writes | ✅ | overwrite per table; rows carry `sha256`, `git_commit`, `loaded_at` |
| Telemetry | ✅ | `@traced` on every public function (enforced by test) |
| Simulated labelled | ✅ | synthetic banner; reliability is "Not assessed" because the reviewers are simulated |
| Configuration | ✅ | no new settings; the CLI pin and validate engine change in CI, stated in the PR |
| Python and R parity | n/a | no label, score or reliability change |

## Test Coverage
Every dashboard query runs in DuckDB on the real tables under the same names. The tiles match pandas, every
widget field exists in its dataset, and the committed JSON matches the builder. Full suite: 665 passed,
14 skipped.

## Verdict
Approve with nits. Confirm the Genie space and the chart widgets on the first dev deploy.
