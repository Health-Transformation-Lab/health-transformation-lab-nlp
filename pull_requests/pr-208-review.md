---
pr: 208
branch: spec/201-024-patel-2022-phenotype
title: "Spec 024: the PerioDx phenotype method of Patel et al. 2022"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: read-only reviewer subagent (Fig. 2 checked at 400 dpi) + coordinator verification
verdict: approve
---

# PR Review: Spec 024: the PerioDx phenotype method of Patel et al. 2022

## Summary
This PR specifies the paper's own method as `algorithm_patel2022`: the chart rule tree (PerioDx Diagnoser,
Fig. 2), the keyword note extractor (PerioDx Extractor), and the stepwise merge (diagnosis codes, then notes,
then chart). It also corrects the docs' claim that the exam-form-first order comes from the paper.

The review found one Critical problem: the stage path was transcribed wrongly. In Fig. 2 every case reaches
"tooth loss due to perio" before stage I or II. It also found seven Important ones. All are fixed in the
second commit, each checked against the figure. Spec, plan and tasks only. Approve.

## Scope of Change
- Files: `specs/024-patel-2022-phenotype/{spec,plan,tasks}.md`, `checklists/requirements.md`, this review
- Range reviewed: `9fb62e1..HEAD`

## CI Status
| Check | Status |
|---|---|
| check (pr-conventions) | ✅ |
| python, postgres, bundle | not run: markdown only (`paths-ignore`) |

## Secrets, PHI and Claims Scan
Clean.
- No data comes in. The paper's data is IRB patient data with no availability statement, and the spec says
  so.
- The paper's figures are cited and labelled as real records from one dental school.
- The DOI, pages and licence (CC BY-NC-ND 4.0) match the PDF.

## Findings
### 🔴 Blocking (Critical)
- **Fixed.** Stage routing. Every path, including cases that fail all four III/IV criteria, passes through
  "tooth loss due to perio" (1–4 teeth is III, 5+ is IV) before the bone-loss box decides I or II. The
  figure's dead end (a III/IV case with no complexity factor and no teeth lost) is the named parameter
  `III_IV_NO_TOOTH_LOSS`. A new acceptance scenario tests it.

### 🟡 Should fix (Important)
- **Fixed.** The entry test "any PD ≥ 4 mm → periodontitis case" is added. "Past loss" now covers CAL and
  recession, not only bone loss.
- **Fixed.** Stage I is "PD 4 mm", as drawn.
- **Fixed.** Extent defines an involved tooth with the figure's stage-specific CAL/PD pairs.
- **Fixed.** Grade routing, re-read from a 400 dpi crop:
  - "≥ 10 per day: No" leads to "HbA1c ≥ 7.0" (yes C, no B);
  - the 0.25–1.0 band enters at "≥ 10 per day", so it never gives A (`GRADE_MID_ENTRY`).
- **Fixed.** A fourth inconsistency in the paper is recorded: the Extractor's stated 91% precision and 87%
  recall give F1 0.89, not the 95% the paper states. US3 cites the 95% with that caveat.
- **Fixed.** The order no longer goes in `DESIGN_GROUPS`, which would have turned script 18's 24 orderings
  into 720. The paper's order is a separate constant and one extra scored row. Per-visit outputs go to a new
  `periodx_visits.csv` (FR-010), so existing datasets stay byte-identical.
- **Fixed.** The confusion matrix has a defined positive class (one-vs-rest per class, and pooled; "no
  diagnosis" is a negative prediction). `confusion_scores` is new, written test first, with an R twin.

### 🔵 Nits (Minor)
- **Fixed.** `remaining_teeth`, `complex_rehab` and `mobility_degree` are `PerioChart` fields in `labels.py`,
  not in `aces.py`.
- **Fixed.** `section_completeness`, `test_periodx.py` and `test_phenotype_patel2022.py` are marked new.
- **Fixed.** FR-004 names `grader_tables.EVIDENCE`, not `METHODS`.
- **Fixed.** The III-versus-IV direction of each split is stated.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets / PHI / org claims | ✅ | |
| Spec for big changes | ✅ | this is the spec; issues #201–#204 |
| Test first, parity | ✅ | tasks put failing tests first; labels, merge and scores have R twins |
| Simulated / synthetic labelled | ✅ | published figures kept apart from synthetic results |
| Commits | ✅ | |

## Verdict
approve. Merge once CI is green; implementation follows in its own PRs.
