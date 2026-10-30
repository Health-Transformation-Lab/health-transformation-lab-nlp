---
pr: 372
branch: spec/369-029-tooth-loss
title: "Spec 029: was a missing tooth lost to periodontitis?"
author: jcbowyer
reviewed_at: 2026-10-30
reviewer: coordinator verification
verdict: approve
---

# PR Review: Spec 029: was a missing tooth lost to periodontitis?

## Summary
This PR specifies a synthetic, Open Dental-shaped extract in its own bronze and silver schemas, a tooth-level
table, and a binary model of "lost to periodontitis". The model is trained on extractions with a recorded
diagnosis and applied to teeth missing without one. Synthetic truth lets the applied model be checked. Spec,
plan and tasks only. Approve.

## Scope of Change
- `specs/029-tooth-loss/{spec,plan,tasks}.md`, `checklists/requirements.md`, this review

## Secrets, PHI and Claims Scan
Clean.
- No organisation, practice, person or plan is named. Open Dental is named only for its published schema.
- No real data. The spec says all rows are generated and labelled synthetic.

## Checks made
- `sites.draw_mouth` (spec 006) already records `missing_reason` per tooth, so the answer key needs no new
  truth process.
- `labels.stage4_rule` already has `teeth_lost_perio` and `all_missing_perio`. The new `expected_perio_loss`
  sits beside them.
- Spec numbers are free: 029 is the next after 028 on main and on the open branches.
- Third molars are excluded by a stated parameter, marked as the repo's choice, not attributed to the
  classification.

## Findings
- 🔵 The Open Dental column list in plan.md is unverified until T001. The spec requires that check before
  code, so the risk is contained.
- 🔵 R and script numbers (15, 45) are provisional because specs 023 and 024 have planned numbers. The plan
  says to take the next free ones at implementation time.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets / PHI / org claims | ✅ | |
| Spec for big changes | ✅ | issues #369–#371 |
| Test first, parity | ✅ | failing tests first in tasks; label rules and metrics have R twins |
| Seeds fixed | ✅ | own stream, fixed defaults |
| Simulated / synthetic labelled | ✅ | |
| Naming | ✅ | bronze keeps source names, silver and gold follow AGENTS.md |

## Verdict
approve. Merge once CI is green.
