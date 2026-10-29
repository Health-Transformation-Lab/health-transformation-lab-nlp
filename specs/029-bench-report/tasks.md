# Tasks: spec 029

- [x] T1 US3 settings, checked at start, with tests
- [x] T2 US1 sources: Databricks statement execution and the DuckDB snapshot, with a fake-client test
- [x] T3 US1 snapshot of the gold tables the report reads (`scripts/snapshot_fixtures.py`)
- [x] T4 US1 the DQ report's SQL and payload; tests recount the measures from the snapshot
- [x] T5 US2 bench registry, in bench order; API routes by bench and report
- [x] T6 US1 React front end from the design; vitest on the real payload
- [x] T7 US3 `app.yaml`, the app's identity in `ops/secrets_register.yaml`, README
- [x] T8 CI workflow `.github/workflows/bench-report.yml`
- [ ] T9 make `healthtransformationlab/bench-report` and move `bench-report/` there with its history
- [ ] T10 deploy the app to the dev workspace and grant its service principal read access
