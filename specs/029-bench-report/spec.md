# Feature Specification: one report app for every bench, starting with the Perio DQ Monitor on live data

**Feature Branch**: `feat/365-029-bench-report`

**Created**: 2026-10-29

**Status**: US1–US3 implemented in `bench-report/`; the app's own repository is still to make (see "Where it lives")

**Input**: "implement the data quality dashboard react mockup we did the other day with real data from databricks
create a separate report fast api and react tell me what to call the repo make the same repo serve multiple bench
marks periobench oralhealthbench etc". The mockup is the React *Perio Data Quality (DQ) Monitor* (a personal
artifact, 2026-10-27), whose light version is spec 019's EHR DQ grader dashboard. Spec 019 left "a hosted React
front end, or the React designs themselves" out of scope: this is that front end.

> Personal learning project; synthetic data only. The app reads the gold tables Load results writes: statuses and
> measurements of synthetic visits, never note text. Every page says the data is synthetic and scored against the
> generator's truth.

## User stories

### US1 - The Perio DQ Monitor, as a FastAPI + React report on the gold tables (P1) #365
A FastAPI backend queries `health_transformation_lab.gold_perio_bench` on a Databricks SQL warehouse and returns one
payload per report; a React front end draws it in the design's layout:

- Header chips: synthetic data, visits, clinics, when the tables were loaded and from which commit, and the source.
- A clinic filter. Completeness, accuracy and the checks follow it; consistency and temporal plausibility are
  measures across clinics and say so.
- **Five domain tiles**, with the dashboard's definitions (spec 019 US2): completeness, accuracy (rules v0 vs truth,
  with the design order beside it), consistency (clinic prevalence spread), temporal plausibility (design rules'
  improved share), reliability **not assessed**. Each has a status pill from display thresholds that the page states
  as starting points, not agreed targets.
- Completeness: missingness by evidence column; visits at each scale; the checks for the clinic.
- Accuracy: each evidence source's share answered and agreement with the truth where it answers; concordance between
  sources.
- Consistency: prevalence by clinic with 95% intervals and the overall line; prevalence by method and scale.
- Temporal plausibility: the stage transition matrix with improvements outlined; improved share by method; the
  injected-error catch rate (synthetic only).

The design's vendor tabs, aims and period filter are dropped: there is one synthetic record system and no study
periods. Its published-prevalence comparison and source cascade have no gold table yet.

### US2 - One app serves every bench (P1) #366
A bench registry in bench order (PerioBench, then OralHealthBench, then AccessBench): each bench names its gold
schema `gold_<bench>`, its status (live, planned, exploratory) and its reports. The API routes by bench and report
(`/api/benches/{bench}/reports/{report}`) and the front end shows the benches as tabs. A bench without a report says
so and names the schema it will read. A new report is one module, one registry entry and one view.

### US3 - Settings checked at start; runs as a Databricks App (P2) #367
Settings declared once (`bench-report/bench_report/settings.py`, README table). A missing or malformed required setting
stops the app at start, naming it; then one cheap authenticated call (the warehouse) before serving. Authentication is
the Databricks SDK's: the app's service principal as a Databricks App (`app.yaml`), a token locally. The app's
identity is in `ops/secrets_register.yaml`. The app only reads.

## Where it lives
Built in `bench-report/`, self-contained (its own `pyproject.toml`, `package.json`, tests and CI workflow, no import
from `python/`), so it can move to its own repository, `healthtransformationlab/bench-report`, with its history
(`git subtree split --prefix bench-report`). Until then the repo-wide tests (wording, bench order, no organisation
names) cover it too.

## Out of scope
- Spec 026's *Records to recheck* page (its tables aren't in the dev workspace yet) and the lab grader; both are a
  report module each when wanted.
- Any change to a measure, label rule or dataset, so no R change: the report reads what Load results wrote.
- Writing anything to Databricks.

## Success criteria
- The report's payload from the dev workspace equals its payload from the committed snapshot (checked 2026-10-29).
- Every report query runs on the snapshot; the tiles match the same measures counted straight from its CSVs.
- `pytest` and `npm test && npm run build` pass in `bench-report/`; CI runs both.
