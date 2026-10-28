# Feature Specification: pipeline telemetry with OpenTelemetry and Azure Application Insights

**Feature Branch**: `014-telemetry`

**Created**: 2026-10-27

**Status**: implemented (Azure resources deployed by the owner)

**Input**: "Implement [MLOps telemetry] on Azure": Application Insights through the Azure Monitor
OpenTelemetry distro, kept inside the free allowance. First step towards self-healing pipelines
(failure detection, root cause, recovery), which need a record of every run, step and failure.

> Personal learning project; synthetic and public data only. Telemetry carries step names, counts,
> durations, pass rates and error types: never note text, PHI or row-level data.

## User stories

### US1 - Every pipeline step is traced (P1)
A step is a span with its name, data label (synthetic / public / simulated) and counts; a failure
records the exception type and message on the span and adds to a failure counter, then re-raises.

### US2 - One switch chooses where telemetry goes (P1)
`DENTAL_TELEMETRY` = `off` (default; tests and CI), `console`, `azure` (Application Insights via
the Azure Monitor OpenTelemetry distro, `APPLICATIONINSIGHTS_CONNECTION_STRING`) or `otlp` (any
OpenTelemetry backend, e.g. self-hosted Grafana Tempo/Loki, Jaeger, SigNoz). `azure` without a
connection string warns and runs with telemetry off: a missing secret never fails a pipeline.

### US3 - Stays inside the free allowance (P1)
- Log Analytics daily cap 0.16 GB (under the 5 GB/month free ingestion per billing account).
- Application Insights retention 90 days (included); workspace retention 30 days.
- Sampling ratio configurable (`DENTAL_TELEMETRY_SAMPLING`, default 1.0: a batch run is a few hundred
  spans, kilobytes, and a dropped failure trace defeats the purpose).
- Only INFO and above from the package logger; no DEBUG.
- Live Metrics on (not billed as ingestion).

### US4 - Infrastructure as code (P2)
`infra/azure/*.tf` (Terraform, azurerm provider): Log Analytics workspace with the daily cap, workspace-based Application
Insights. CI checks formatting and validates it (`terraform fmt -check`, `terraform validate`). Connection string goes to the Databricks secret scope `dental`, key
`appinsights_connection_string`; Databricks jobs read it and pass it to the scripts.

### US5 - Queries for the questions DataOps asks (P2)
`docs/telemetry.md`: KQL for failures by step and error type, step duration trends, data-quality
pass-rate trends, and the last successful run per pipeline.

## Out of scope (next spec)
The "pipeline doctor": classifying failures, choosing a recovery, escalation and notification, and
its evaluation on this repo's real incidents.

## Revision 2026-10-27: Terraform instead of Bicep
The infrastructure moved from Bicep (Azure-only) to Terraform with the azurerm provider: the same
resources and limits, one tool that also manages Databricks (the Databricks Terraform provider) and
other clouds. Terraform also creates the resource group. Its state file holds the connection string,
so it is git-ignored.

## Revision 2026-10-28: every call, with a common header
As cdh-lava-core does (`with tracer.start_as_current_span(...)` in every method, service and cloud-role
names built from data product and environment): every public function and method in the package
carries `@traced`, the decorator form of `with trace_call(...)`, which yields a logger with the same
header. Header on every span and log line: `data_product_id`, `environment`, `service.namespace`;
resource `service.name` is the data product. A per-parent budget (3 spans per function, the rest
counted) keeps hot loops from flooding the free allowance; with telemetry off the decorator is a direct
call. A test fails if a public function is missing `@traced`.

## Revision 2026-10-28: verbosity levels
`DENTAL_TELEMETRY_LEVEL` = `step` (scripts and pipeline steps), `call` (default: also pipeline-level
functions) or `detail` (also per-item helpers). Each function's level is measured by
`scripts/39_telemetry_levels.py` (each pipeline in its own process under `DENTAL_TELEMETRY_PROFILE`:
calls per parent call and time per call) and kept in `telemetry_levels.yaml`; hand edits marked
`manual: true` survive reruns. Below the chosen level `@traced` is a direct call. Site build: 1 / 6 /
20,691 spans at step / call / detail. `37_cal_reliability.py` now writes its gzip without a timestamp,
so reruns don't change the committed file.
