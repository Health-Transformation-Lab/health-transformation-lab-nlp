---
pr: 205
branch: spec/198-023-medical-record-features
title: "Spec 023: synthetic medical-record features for the status classifier"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: read-only reviewer subagent + coordinator verification
verdict: approve
---

# PR Review: Spec 023: synthetic medical-record features for the status classifier

## Summary
This PR specifies a seeded synthetic medical record for each person, and three runs of the status classifier
(dental only, dental and medical, medical only), as in Patel et al. 2026's experiments 1 and 5. The runs use
the paper's 4 classes and a 70/30 stratified split, with per-class sensitivity, specificity, AUC and Brier
score that have R twins. The review found four Important problems and one Minor one, all fixed in the second
commit. Spec, plan and tasks only. Approve.

## Scope of Change
- Files: `specs/023-medical-record-features/{spec,plan,tasks}.md`, `checklists/requirements.md`, this review
- Range reviewed: `9fb62e1..HEAD`

## CI Status
| Check | Status |
|---|---|
| check (pr-conventions) | ✅ |
| python, postgres, bundle | not run: markdown only (`paths-ignore`) |

## Secrets, PHI and Claims Scan
Clean.
- No data comes in.
- The paper's Table 2 averages (84/86/57) are cited and match the PMC full text.
- Every link to periodontal status must cite a published source, checked before use. The candidate sources
  are listed as unchecked.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important)
- **Fixed.** "Every file byte-identical, and the columns are added" contradicted itself. The medical record
  is now its own file, `medical_record.csv`, joined on `person_id`.
- **Fixed.** The generator has no sex column, so "medical only" is the medical features plus age. Sex stays
  a spec 013 G11 gap.
- **Fixed.** ASA class is derived from conditions, so it carries medical signal into the dental set, as it
  does in the paper, where ASA is a dental-record factor. This is now stated, and a `dental_no_asa` run
  measures it.
- **Fixed.** The column names are settled: `is_<condition>`, `systolic_bp_mmhg`, `diastolic_bp_mmhg`,
  `asa_class_code`. HbA1c reuses the existing `hba1c` column. A `_mmhg` row goes into AGENTS.md's suffix
  table in the implementation PR if the results go to gold.

### 🔵 Nits (Minor)
- **Fixed.** The odds-ratio test is the age-adjusted (Mantel–Haenszel) one. The generator conditions only on
  status and age band, so it recovers the cited value by construction.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets / PHI / org claims | ✅ | |
| Spec for big changes | ✅ | this is the spec; issues #198–#200 |
| Test first, parity | ✅ | failing tests first in tasks; new metrics get R twins |
| Seeds fixed | ✅ | own seeded stream, fixed default |
| Simulated / synthetic labelled | ✅ | results labelled synthetic; the paper's figures kept apart |
| Commits | ✅ | |

## Verdict
approve. Merge once CI is green; implementation follows in its own PRs.
