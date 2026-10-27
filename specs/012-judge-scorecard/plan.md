# Implementation Plan: Judge-backed model scorecard on Databricks

**Branch**: `012-judge-scorecard` (work lands on `claude/awesome-cannon-7xnqm6`) | **Date**: 2026-10-27 |
**Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/012-judge-scorecard/spec.md`

## Summary

Deploy dev on every merge; load every system's per-chart answers on the 240 review charts into
a table; judge each chart once for its own status and each unique (chart, answer) once for a
verdict, with the existing quote gate; compute every README phenotyping metric against the truth
and against the judge with the existing scorers; show it all on a two-page AI/BI dashboard
deployed with the bundle, with MLflow traces per call. Research: [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12 (CI), base R (parity)

**Primary Dependencies**: existing only: pandas, numpy, mlflow (`track` extra), Databricks CLI
bundle; the judge uses the stdlib HTTP client already in `judge.py`

**Storage**: Unity Catalog Delta tables in `dental_omop.gold_dental_omop_perio`; committed CSV
twins in `data/datasets/judge/`

**Testing**: pytest (simulated judge, no network), R parity test, bundle structure tests

**Target Platform**: Databricks serverless jobs + SQL warehouse; GitHub Actions

**Project Type**: data pipeline + bundle resources

**Performance Goals**: full judge run ≤ 30 min; ≤ US$5 (SC-005)

**Constraints**: synthetic, de-identified notes only; the judge never computes a metric;
identical resource names in every target

**Scale/Scope**: 240 charts, 38 systems, ≤ 1,680 judge calls

## Constitution Check

| Principle | Status | How |
|---|---|---|
| 0 Personal, not affiliated | ✅ | no organization claims; endpoints named as Databricks documents them |
| I Synthetic only, no PHI | ✅ | judge reads `review_key.csv` notes, which passed de-identification and the leak gate |
| II Python and R | ✅ | metrics reuse parity-tested scorers; new agreement/difference computations get an R twin and a parity check |
| III Test-first | ✅ | each task starts with a failing test (simulated judge, no network) |
| IV Honest outputs | ✅ | judge output labelled *LLM judgment*; simulated runs `simulated_*`; calibration source (truth, not humans) stated |
| V Published evidence | ✅ | AAP/EFP criteria unchanged (`judge.CRITERIA`); Rogan-Gladen as in spec 002 |
| VI Simple, seeded | ✅ | no new dependency; bootstrap seeded |
| Judges calibrated before use | ✅ | judge agreement with truth is computed and shown before/next to judge metrics |

Re-checked after design: no violations.

## Project Structure

### Documentation (this feature)

```text
specs/012-judge-scorecard/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/judge-output.md
└── tasks.md            # /speckit-tasks
```

### Source Code

```text
.github/workflows/deploy.yml               # push to main: matrix [dev, uat]
databricks.yml                             # judge_endpoint dev default; dashboard resource
databricks/resources/jobs.yml              # judge_scorecard job
databricks/resources/dashboards.yml        # AI/BI dashboard resource
databricks/dashboards/scorecard.lvdash.json  # two pages: Phenotyping, De-identification
databricks/notebooks/07_judge_scorecard.py # runs the scorecard on Databricks, writes tables
python/dental_omop_nlp/judge.py            # status prompt (judge-v3), gate_status
python/dental_omop_nlp/judge_scorecard.py  # answers, queue, run judge (resumable), metrics
python/scripts/36_judge_scorecard.py       # local / --simulated / --export
python/tests/test_judge_scorecard.py
r/R/11_judge_scorecard.R                   # twin: differences and judge agreement
r/tests/test_parity.R                      # + judge scorecard section
data/datasets/judge/                       # committed CSV twins
README.md, docs/results.md                 # link to dashboard; judge columns
```

**Structure Decision**: one library module (`judge_scorecard.py`) used by both the local script
and the Databricks notebook, as for the existing benchmark.

## Complexity Tracking

None.
