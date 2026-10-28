---
pr: 240
branch: spec/234-026-case-profiles
title: "Spec 026: case profiles and record-mismatch flags"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve-with-nits
---

# PR Review: Spec 026: case profiles and record-mismatch flags

## Summary
The PR adds spec 026's spec, plan, tasks and quality checklist. It covers KEEPER-style case profiles (US1), six
record-mismatch rules scored against the generator's truth (US2), and a "Records to recheck" page with Genie
(US3). The first review found no blocking issues, but it did find six important design problems in the US2 rules
and their scoring. I reproduced each one against the built study (see Findings), and all are fixed in the revised
spec, plan and tasks. The data claims (counts, columns, reserved script numbers) hold. Verdict: approve with
nits. Docs only; no code.

## Scope of Change
- Files changed: 5 (spec, plan, tasks, checklist, this review), docs only
- Areas touched: specs, pull_requests
- Commits: the spec, the plan, the tasks, then the review fixes
- Range reviewed: `origin/main..spec/234-026-case-profiles`

## CI Status
| Check | Status |
|---|---|
| check (PR conventions) | pass on the first push; re-runs on this push |
| python, r-parity, postgres, bundle | not affected (no code); `test_wording.py` passes locally on the tracked files |

## Secrets, PHI and Claims Scan
- **Secrets:** clean.
- **PHI / real data:** clean. Only synthetic counts are quoted.
- **Organization claims:** clean. KEEPER is cited from its paper; no organization is named.

## Strengths
- Every decision names the column it uses, and each column exists in `visits_structured.csv` or `visits_truth.csv`.
- The stage-drop rule reuses `plausibility.check_history`, so there is no second definition of a drop.
- Not-checkable visits, the KEEPER citation, the synthetic label and the Words framing are all explicit.
- Tests come first in every story, with one PR per issue.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
All six were fixed in this PR. Each entry says what was wrong, how I checked it, and the fix.

- **Rule "code higher than the chart" flagged a real stage III chart.**
  - *Wrong:* a chart with low CAL and bone loss is still stage III when a tooth was lost or PD is 6 mm or more.
  - *Checked:* `labels.py`; on the built study the first-draft rule flagged 4 visits, one with a stage III chart reading.
  - *Fix:* the rule also needs no tooth lost and PD under 6 mm, and is limited to stage III codes (the synthetic codes stop at III).
- **Rule "code lower than the chart" had no sound source.**
  - *Wrong:* PD ≥ 5 mm with BOP > 30% fits gingivitis (pseudopockets; > 30% is generalized gingivitis).
  - *Checked:* all 26 of its flags are also flagged by the chart-reading rule.
  - *Fix:* the rule is now CAL ≥ 3 mm or bone loss ≥ 15%, which is beyond stage I. A new "only this rule" score shows any rule that adds nothing.
- **The stage-drop rule scored only the later visit.**
  - *Wrong:* in a prototype, about half the drops had the earlier, higher code wrong.
  - *Fix:* the evidence names the earlier visit, and a flag is true when either code is wrong.
- **SC-004 asked for at least half the injected errors, which can't be reached.**
  - *Checked:* only 34 of the 45 injected-error visits have a code.
  - *Fix:* SC-004 now reports the catch rate against that 34/45 ceiling and beside the temporal checks' rate.
- **`item_value_num` broke the rule that `_num` columns are bigint** (`test_sql_conventions.py`).
  - *Fix:* each value is a short label with a unit column (`item_value_name`, `item_unit_name`), as US1 builds it.
- **Recall had three denominators.**
  - *Fix:* there is one: the visits a rule can check, with that count shown. "Any rule" covers every coded visit.

### 🔵 Nits / suggestions (Minor)
Fixed:
- The radiograph rule's reverse direction can't fire (the synthetic AI reads only stage II or III); it is now one direction.
- US2 test fixtures now set the other evidence so only the intended rule fires.
- The plan no longer says `notes` is never read. It is the note reader's status, and the profile shows it as one.
- `build_profiles` has one signature everywhere: `(visits)`.
- A missing code reads "not recorded" in the profile and has outcome "no code" in the rules.
- Stage drop is not checkable when the patient has no earlier periodontitis code.
- Category "Diagnostic tests" is renamed "Tests and imaging".
- `wrong_code_count` is renamed `code_truth_mismatch_count`; the plan's opening line is reworded.
- The summary table is renamed `dq_mismatch_rule`, to match the other DQ summary tables.
- The new tables' relation to `fact_visit_evidence` and `dq_injected_error` is stated (join on `visit_id`; they replace nothing).
- US3's Genie-wording scenario is now tested through the space's instructions; Genie's own answers are LLM output, checked by hand on dev.
- Per-clinic injected-error counts are marked too few to read.
- The task dependency now points at `check_history`, not the profile. The plan cites `labels.LABELS`.
- An "Out of scope" section is added, as in spec 024.

Not fixed:
- The PR body footer is rewritten by the posting tool; nothing in the repo to fix.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | Yes | |
| Synthetic only, no PHI | Yes | |
| No organization claims; vendors cited | Yes | |
| Test first | Yes | Every story starts with failing tests |
| Python and R in parity | Planned | Rules and scores twinned in `r/R/15_spec026.R`; profiles are display only |
| Simulated is labelled simulated | Yes | Every result is labelled synthetic, against the generator's truth |
| Spec for big changes | Yes | This is the spec |
| Words | Yes | `test_wording.py` passes on the tracked files |
| Issues and branches | Yes | #234–#236 keyed `026 US<n>`; branch `spec/234-026-case-profiles`; `Refs` all three |

## Test Coverage
Docs only. `test_wording.py` and `test_no_org_references.py` pass with the files tracked. I prototyped the rule
counts quoted in the plan against the built study in a throwaway script, not committed.

## Verdict
Approve with nits. The spec, plan and tasks are consistent with each other and with the data.
