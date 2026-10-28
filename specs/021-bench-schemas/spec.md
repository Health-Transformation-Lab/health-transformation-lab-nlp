# Feature Specification: Databricks schemas are named for the three benches

**Feature Branch**: `feat/141-021-bench-schemas`

**Created**: 2026-10-28

**Status**: implemented

**Input**: "our schema names should reflect the new names access_bench perio_bench and oral_health_bench with
bronze silver gold"

> Personal learning project; synthetic data only. No metric, label rule or result changes: the same tables,
> files and model under new schema names, plus empty schemas for two benches that have no pipeline yet.

The bundle had one set of layer schemas, `landing_`/`bronze_`/`silver_`/`gold_dental_omop_perio`. The work is
now framed as three benches: **perio_bench** (periodontal status from charts, everything built so far),
**access_bench** (whether answers help people get care) and **oral_health_bench** (the umbrella scorecard).

## User stories

### US1 - Schemas are named for the benches (P1) #141

| Was | Now |
|---|---|
| `landing_dental_omop_perio` (the `data` volume) | `landing_perio_bench` (the `data` volume) |
| `bronze_dental_omop_perio` | `bronze_perio_bench` |
| `silver_dental_omop_perio` | `silver_perio_bench` |
| `gold_dental_omop_perio` (tables, `perio_note_classifier`) | `gold_perio_bench` (tables, `perio_note_classifier`) |
| (none) | `bronze_access_bench`, `silver_access_bench`, `gold_access_bench` (empty) |
| (none) | `bronze_oral_health_bench`, `silver_oral_health_bench`, `gold_oral_health_bench` (empty) |

- Catalog stays `dental_omop`; names are the same in every target (AGENTS.md, Conventions).
- Every job, notebook default, dashboard query, doc and diagram uses the new names. A test fails if the old
  name appears anywhere except the migration and the legacy bundle entries.
- The telemetry data product (`service.name`) becomes `perio_bench`, as in the schemas.

### US2 - Existing perio data and model carry over (P1) #142

- A migration (notebook 12) runs first in the **Load results** job after each deploy. If the old schemas
  exist, it copies every table to the same name in the matching new schema, the landing volume's files, and
  each `perio_note_classifier` version (with its aliases) into the new registered model.
- Rerunning adds nothing: a table already in the new schema is skipped, a file already copied is skipped, a
  model version already copied (tagged with its source version) is skipped. A target that never had the old
  schemas (fresh uat or prod) does nothing.
- Row counts are checked after each table copy; a mismatch fails the job.
- The old schemas, volume and model stay. They keep `prevent_destroy`, so a deploy can't drop them; the bundle
  keeps declaring them (as legacy) until they are checked and removed by hand.

## Why the old schemas stay declared

The old schemas and the volume have `prevent_destroy`. Renaming them in place would make the deploy fail
(or, for the registered model, replace it and lose its versions before the migration copies them). So the new
schemas are new bundle resources, and the old ones stay under their old keys, marked legacy. A later change
unbinds and removes them (docs/deployment.md, "Retiring the legacy schemas").

## Out of scope

- Pipelines, tables or questions for access_bench and oral_health_bench.
- Dropping the old schemas.
- Historical specs (012, 016, 018) and PR reviews keep the names they were written with.
