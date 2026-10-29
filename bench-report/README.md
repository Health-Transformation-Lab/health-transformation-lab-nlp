# bench-report

Reports for the Health Transformation Lab benches, read live from the Databricks gold tables: a FastAPI backend and
a React front end. One app serves every bench, in bench order: **PerioBench**, then **OralHealthBench**, then
**AccessBench** (spec 029, `../specs/029-bench-report/`).

> Personal learning project, not affiliated with any employer or organization. **Synthetic data only**: every visit
> comes from the study's generator and is scored against the generator's own truth, not clinical performance.

| Bench | Status | Reports | Gold schema |
|---|---|---|---|
| PerioBench | live | **Perio Data Quality (DQ) Monitor**: is this dental record fit for finding gum disease? | `gold_perio_bench` |
| OralHealthBench | planned | none yet | `gold_oral_health_bench` |
| AccessBench | exploratory | none yet | `gold_access_bench` |

The DQ Monitor is the React design of 2026-10-27 on real tables: five domain tiles (Zozus completeness, accuracy and
consistency; Kahn temporal plausibility; Liaw reliability, not assessed until real reviewers label charts), then one
section per domain, filtered by clinic. Its measures are the EHR DQ grader dashboard's (spec 019), so the two agree.

## Layout

```
bench_report/
  settings.py      every setting, declared once and checked at start
  sources.py       DatabricksSource (SQL warehouse, statement execution API) and FixtureSource (DuckDB snapshot)
  benches.py       the bench registry and each bench's reports
  reports/         one module per report: its SQL and the payload it returns
  main.py          FastAPI: /api/health, /api/benches, /api/benches/{bench}/reports/{report}; serves web/dist
web/               Vite + React + TypeScript; one view per report in src/reports/
tests/             pytest, on tests/fixtures/ (a snapshot of the gold tables)
scripts/snapshot_fixtures.py   refresh that snapshot from Databricks
app.yaml           run as a Databricks App
```

## Settings

| Variable | Needed | Meaning |
|---|---|---|
| `DATABRICKS_HOST` | for Databricks | workspace URL, `https://...` |
| `DATABRICKS_WAREHOUSE_ID` | for Databricks | SQL warehouse id: SQL warehouses → the warehouse → Overview → ID (16 hex characters) |
| `BENCH_REPORT_SOURCE` | no | `databricks` (default) or `fixtures` (the committed snapshot, no workspace) |
| `BENCH_REPORT_CATALOG` | no | default `health_transformation_lab`, the same in every environment |
| `BENCH_REPORT_CACHE_SECONDS` | no | how long a report is reused, default 300 |
| `BENCH_REPORT_FIXTURES_DIR` | no | snapshot folder, default `tests/fixtures` |

Authentication is the Databricks SDK's own; the app never reads a credential's value. As a Databricks App it uses the
app's service principal. Locally, a workspace personal access token in `DATABRICKS_TOKEN` (Settings → Developer →
Access tokens, scope `all-apis`, 15 days at most; it's in `../ops/secrets_register.yaml`). A missing or malformed
setting stops the app at start, naming it; then one call checks the warehouse before anything is served.

The identity needs `CAN USE` on the warehouse and, in Unity Catalog, `USE CATALOG` on `health_transformation_lab` and
`USE SCHEMA` plus `SELECT` on each `gold_<bench>` schema. Nothing writes: the app only reads.

## Run it

```bash
pip install -e ".[dev]"
cd web && npm ci && npm run build && cd ..
DATABRICKS_WAREHOUSE_ID=<id> uvicorn bench_report.main:app --port 8000     # live, from Databricks
BENCH_REPORT_SOURCE=fixtures uvicorn bench_report.main:app --port 8000     # the snapshot, no workspace
```

Open http://localhost:8000. For front-end work, run the API as above and `cd web && npm run dev` (Vite proxies
`/api` to port 8000).

## Test

```bash
pytest -q                       # settings, sources, registry, report measures, API
cd web && npm test && npm run build    # front end on the real payload, and the type check
```

The report's SQL runs on both engines; on the dev workspace of 2026-10-29 the Databricks payload and the snapshot's
are identical. Shares are computed in Python from counts, so the two engines can't round differently.

Refresh the snapshot after the gold tables change (overwrites every file, and the front end's payload):

```bash
DATABRICKS_WAREHOUSE_ID=<id> python scripts/snapshot_fixtures.py
```

## Run it as a Databricks App

1. Compute → Apps → Create app → Custom, name `bench-report`. Add a resource: SQL warehouse, permission *Can use*,
   key `sql-warehouse`.
2. Grant the app's service principal (shown on the app's Authorization tab) `USE CATALOG`, `USE SCHEMA` and `SELECT`
   as above.
3. Build and deploy:

```bash
cd web && npm ci && npm run build && cd ..
databricks sync . /Workspace/Users/<you>/bench-report
databricks apps deploy bench-report --source-code-path /Workspace/Users/<you>/bench-report
```

## Add a report or a bench

1. `bench_report/reports/<name>.py`: its `SQL` (with `{gold}` for `<catalog>.gold_<bench>`), the gold tables it
   reads, and `shape(rows)` returning the payload. Lowercase SQL that DuckDB also runs.
2. Add it to the bench's `reports` in `bench_report/benches.py` (a bench is listed even with none).
3. `web/src/reports/<Name>.tsx`, and one line in `VIEWS` in `web/src/App.tsx`.
4. Rerun `scripts/snapshot_fixtures.py`, then add tests that count the measures straight from the snapshot.
