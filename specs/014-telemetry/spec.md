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
`infra/azure/main.bicep`: Log Analytics workspace with the daily cap, workspace-based Application
Insights. CI compiles it. Connection string goes to the Databricks secret scope `dental`, key
`appinsights_connection_string`; Databricks jobs read it and pass it to the scripts.

### US5 - Queries for the questions DataOps asks (P2)
`docs/telemetry.md`: KQL for failures by step and error type, step duration trends, data-quality
pass-rate trends, and the last successful run per pipeline.

## Out of scope (next spec)
The "pipeline doctor": classifying failures, choosing a recovery, escalation and notification, and
its evaluation on this repo's real incidents.
