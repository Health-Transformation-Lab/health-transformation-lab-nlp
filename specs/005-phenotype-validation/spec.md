# Feature Specification: Integrated phenotype, longitudinal plausibility, clinic prevalence, data quality, prediction

**Feature Branch**: `005-phenotype-validation`

**Created**: 2026-10-25

**Status**: v1 implemented on synthetic data

**Input**: "Cover the remaining study-design use cases: combine the best sources
into one phenotype, validate it over time and against external evidence,
estimate clinic-level prevalence, assess data quality, and build a prediction
model." Differences from the study design are tracked in
[docs/action_items.md](../../docs/action_items.md).

> Personal learning project; synthetic data; public sources only.

## User stories

### US1 - Integrated five-category phenotype with a configurable source order (P1)
Combine sources into one call in five categories (healthy/gingivitis, stage
I–IV). Default order: exam form → diagnosis code → note NLP → periodontal-chart
algorithm. The order is data, not code, and every ordering of those four is
scored so the order can change if another source proves more accurate.

- **Given** the default order and a visit where the exam form is silent, **Then** the diagnosis code decides.
- **Given** all 24 orderings, **Then** each is scored against reviewers on a selection half and reported on a held-out half (the order is not chosen and judged on the same charts).
- Reliability and the acceptance test can be reported on 5 categories (Python = R).

### US2 - Longitudinal histories and temporal plausibility (P1)
Synthetic patients have histories: attachment and bone loss don't reverse;
progression speed follows grade risk; treatment lowers pocketing and bleeding;
a small, known share of charting errors is injected. Checks flag implausible
changes between consecutive visits.

- **Given** a periodontitis patient, **Then** later visits are never healthy/gingivitis in the truth.
- **Given** an injected error, **Then** the checks flag it (recall reported).
- Checks: periodontitis → no periodontitis; stage drops; CAL drops > 1.5 mm; RBL drops > 5 points; teeth lost decreases (Python = R).

### US3 - Clinic-level prevalence and external comparison (P2)
Each person belongs to a synthetic clinic with its own case mix and charting
habits. Prevalence of periodontitis and of stage III–IV per clinic, with 95%
Wilson intervals, from the phenotype and from truth; compared with published
US estimates (NHANES 2009–2014, CDC/AAP definitions) with caveats.

### US4 - Data quality checks (P2)
Conformance, completeness and plausibility checks, after the harmonized
data-quality terminology used by OHDSI's Data Quality Dashboard; pass rates
overall and per clinic.

### US5 - Prediction model (P3)
Predict periodontitis progression (stage up at the next visit) from the
current visit's phenotype, chart values, risk factors and age; held-out
people; AUROC with bootstrap CI; feature importance compared with established
risk factors (smoking, diabetes, age, existing disease).

## Requirements
- FR-001 `phenotype.collapse5`, `RULES_DESIGN` (default) and `RULES_V0` (alternative); `algorithm_design` column.
- FR-002 `scripts/18_phenotype_order.py`: 24 orderings, split-half selection, held-out acceptance test.
- FR-003 `synthetic.draw_history`; `plausibility.py` checks; injected-error flag in the answer key only.
- FR-004 `prevalence.py` (Wilson CI) + benchmark table; `scripts/19_prevalence.py`.
- FR-005 `dq.py`; `scripts/20_data_quality.py`.
- FR-006 `prediction.py`; `scripts/21_predict_progression.py`.
- FR-007 R twins: 5-category collapse, plausibility flags, prevalence + Wilson CI; parity-tested.

## Success criteria
- SC-001 Tests per story; parity OK; CI green.
- SC-002 Every output on simulated reviewers is labelled simulated.

## Assumptions
- Progression rates, treatment effects, clinic mixes and error rates are planning placeholders.
- Grade from direct 5-year evidence is not generated (histories span ≤ 3 years).
