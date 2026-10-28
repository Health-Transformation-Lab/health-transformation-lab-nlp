# Implementation Plan: bench schemas (spec 019)

**Spec**: [spec.md](spec.md) · **Issues**: #141 (US1), #142 (US2)

## Approach

1. **Names in one place.** `python/dental_omop_nlp/schemas.py` declares the benches, their layers, the legacy
   names and the migration plan (pure functions, tested). Notebook 12 and the tests import it.
2. **Bundle.** `databricks/resources/unity_catalog.yml` adds `perio_bench_*`, `access_bench_*` and
   `oral_health_bench_*` schema resources and a `perio_bench_data` volume, all `prevent_destroy`. The old
   `landing`/`bronze`/`silver`/`gold` schemas and `data` volume keep their keys under `legacy_domain`
   (`dental_omop_perio`). `mlops.yml` adds `perio_bench_note_classifier` (name `perio_note_classifier`, in
   `gold_perio_bench`) and keeps the old model resource as legacy. Every job parameter points at the
   `perio_bench_*` resources. The `domain` variable is replaced by `legacy_domain`.
3. **Rename.** Notebook defaults, the dashboard's SQL, `runlog`, `model_registry`, `delta`, `telemetry`
   (`DATA_PRODUCT = "perio_bench"`), docs, diagrams and AGENTS.md use `<layer>_perio_bench`.
4. **Migration.** Notebook 12 (`12_migrate_bench_schemas.py`), first task of **Load results**, before spec
   018's `migrate_gold_names` (which then runs on `gold_perio_bench`).

## Tests first

- `test_schemas.py`: the 11 names; the migration plan (copy, skip, nothing when the old schema is gone); model
  versions to copy (skips ones tagged as copied).
- `test_bundle.py`: the bundle declares exactly the bench schemas plus the legacy four; jobs use
  `perio_bench_*`; the model lives in `gold_perio_bench`; the load job runs the migration first.
- `test_no_legacy_names.py`: `dental_omop_perio` appears only in the allowed files.

## Environments

dev, uat and prod all change the same way on their next deploy (same names everywhere). The migration only has
work to do where the old schemas exist (dev today).
