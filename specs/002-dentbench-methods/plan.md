# Implementation Plan: Reuse GlobalDentBench evaluation methods

**Branch**: `002-dentbench-methods` | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)

## Summary

Add a harm-severity grading of errors, difficulty levels per chart, and a judge
bake-off; report them in Python and R; document what was reused from
GlobalDentBench and what was deliberately done differently.

## Technical Context

**Language/Version**: Python 3.10+, R 4.2+ (base R)
**Primary Dependencies**: none new
**Testing**: pytest; `r/tests/test_parity.R`
**Constraints**: severity matrix is DRAFT pending clinician sign-off

## Constitution Check

| Principle | Status |
|-----------|--------|
| I. Synthetic only | Pass: no new data sources; GlobalDentBench data not used |
| II. Two languages | Pass: harm rates and per-level table in both; parity extended |
| III. Test-first | Pass: T003–T005 before code |
| IV. Honest outputs | Pass: matrix labelled DRAFT; simulated judges named `sim-judge-*` |
| V. Published evidence | Pass: each reused method cites the paper; departures stated |
| VI. Simple, seeded | Pass: bootstrap seeded; no new deps |

## Source changes

```text
python/dental_omop_nlp/harm.py          NEW  severity matrix, unsafe rates
python/dental_omop_nlp/study.py         difficulty column
python/dental_omop_nlp/reliability.py   unsafe/s2 rates; by-level table
python/dental_omop_nlp/judge.py         SimulatedJudge profiles
python/dental_omop_nlp/cost_effectiveness.py  kappa + CI in calibration; bakeoff()
python/scripts/13_reliability.py        writes by_level.csv
python/scripts/15_judge.py              --candidates; bake-off
python/scripts/16_cost_effectiveness.py uses selected judge
r/R/04_reliability.R                    harm + by-level twins
r/tests/test_parity.R                   extended
docs/dentbench_methods.md, docs/references.md   NEW
```
