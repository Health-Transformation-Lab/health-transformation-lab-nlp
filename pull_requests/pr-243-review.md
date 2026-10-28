---
pr: 243
branch: feat/234-026-case-profiles
title: "Build a KEEPER-style case profile for every synthetic visit (026 US1)"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve-with-nits
---

# PR Review: Build a KEEPER-style case profile for every synthetic visit (026 US1)

## Summary
The PR adds `case_profile.build_profiles`, which gives one KEEPER-style profile per synthetic visit: nine
categories, structured values only. It also adds the gold table `fact_case_profile_item`, built from
`visits_structured.csv` at load time, and gives the DQ Genie space the table, an instruction and a sample
question. The review found no blocking issues. It found two important bugs (a numpy 2 boolean shown as "1", and
the first visit shown as "visit 0") and five minor ones. I reproduced each one with a failing test, and all are
fixed in the follow-up commit. Verdict: approve with nits. The gold ERD PNGs still need re-rendering.

## Scope of Change
- Code commits, after the spec commits from #240:
  - 767a50b Build a KEEPER-style case profile for every synthetic visit
  - Tick off spec 026's US1 tasks
  - Show profile values the same whatever their type, and number visits from 1
- Areas touched: python (new module, `grader_tables`, `gold_names`, `dashboards`), diagrams (gold model, ERD sources), databricks (Genie JSON), docs, specs (tasks ticked)
- Range reviewed: `origin/spec/234-026-case-profiles..feat/234-026-case-profiles`

## CI Status
| Check | Status |
|---|---|
| python | pending on push; locally `pytest -q tests`: 988 passed, 15 skipped |
| check, postgres, r-parity, bundle | pending on push; no SQL, R or bundle change |

## Secrets, PHI and Claims Scan
- **Secrets:** clean.
- **PHI / real data:** clean. The profile reads statuses and measures only. `notes` in `visits_structured.csv` is the note reader's status, and the longest value is 34 characters.
- **Organization claims:** clean. KEEPER is cited from its paper.

## Strengths
- **Deterministic:** the output doesn't depend on row order.
- **Fast:** 0.6 s for 4,343 visits (112,918 rows).
- **Load results handles it as is:** the new table goes through `dq_tables` and `to_gold`, every column is known to `gold_names`, and the bigint columns match their `_num` and `_id` suffixes.
- **Small committed footprint:** the profile isn't committed as a second 6 MB copy of the evidence.
- **Telemetry:** the public functions are `@traced`. **Wording:** the Words rule holds.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
Both fixed, each with a test:
- `case_profile.py` `_shown`:
  - *Wrong:* it tested numpy booleans by type name, which is "bool" in numpy 2, so `np.True_` showed as "1".
  - *Checked:* reproduced with `_shown(np.True_)`.
  - *Fix:* it now uses `isinstance(value, (bool, np.bool_))`.
- "visit number for the patient":
  - *Wrong:* it showed `visit_seq`, which starts at 0.
  - *Fix:* it now shows `visit_seq + 1`.

### 🔵 Nits / suggestions (Minor)
All fixed:
- `_shown` raised on `pd.NA` and showed "nan" for `np.float32('nan')` and "NaT" for `pd.NaT`. It now checks `pd.isna` first, and `build_profiles` converts every column to one scalar type, so nullable dtypes give the same profile.
- The next visit was picked by `visit_seq`, while `check_history` orders by date. Both now use date, with a test where the two disagree.
- The treatment items said "procedure codes" but hold the status read from them. They are renamed "status from periodontal procedure codes, ...".
- The Genie instruction didn't explain `none` or the five plausibility flag names. It does now, with a test.
- The test gaps (numpy and pandas scalars, date versus sequence order) are covered by the tests above.

Not fixed:
- The gold ERD PNGs are not re-rendered: the draw.io viewer is blocked in this environment. The sources and `data_model.md` are current.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | Yes | |
| Synthetic only, no PHI | Yes | Statuses and measures only |
| No organization claims; vendors cited | Yes | |
| Test first | Yes | Every behaviour and every fix had a failing test first |
| Python and R in parity | N/A | Profiles are display only; US2's rules and scores get the R twin |
| Simulated is labelled simulated | Yes | The Genie instructions require "On synthetic data:" |
| Paths | Yes | `DATASETS_DIR` |
| SQL and data names | Yes | `test_sql_conventions.py`: every column has a legal suffix and type |
| Telemetry | Yes | |
| Words | Yes | `test_wording.py` |
| Configuration, secrets register, alerts | N/A | |

## Test Coverage
`test_case_profile.py` has 23 tests. They cover the categories, units, the missing-value labels, the next visit
and its flags, Python, numpy and pandas scalars, nullable dtypes, date order, and the whole study.
`test_grader_tables`, `test_gold_model` and `test_dashboards` cover the gold table and Genie. The full suite passes
locally, and `ruff check` is clean on the changed files.

## Verdict
Approve with nits. It can merge once #240 has merged and CI is green. Re-render the ERD PNGs when the viewer is reachable.
