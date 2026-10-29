# Plan: spec 029, the report app

- **Backend** (`bench-report/bench_report/`): FastAPI. `settings.load()` checks every setting; `sources.py` has a
  `DatabricksSource` (Databricks SDK statement execution: waits, cancels past a timeout, reads every chunk, converts
  types from the manifest) and a `FixtureSource` (DuckDB over the committed snapshot, same three-part names). A
  report is SQL with `{gold}` plus a `shape()`; its queries run in parallel and the payload is cached per report
  (`BENCH_REPORT_CACHE_SECONDS`), one lock per report so a cold warehouse is queried once.
- **One definition of each measure**: the SQL follows `python/health_transformation_lab_nlp/dashboards.py` `DQ_SQL`;
  shares are computed in Python from counts so Databricks (decimal averages) and DuckDB (float averages) can't
  round differently.
- **Front end** (`bench-report/web/`): Vite, React 18, TypeScript, the design's CSS and SVG charts ported as
  components. Hash routing `#/<bench>/<report>`; `VIEWS` maps a report to its view.
- **Tests**: pytest on the snapshot (measures recounted from the CSVs, API, settings, a fake SDK client); vitest on
  the real payload (`web/src/__fixtures__/`, checked current by pytest).
- **Deploy**: `app.yaml` for Databricks Apps with a `sql-warehouse` resource; the front end is built first.
