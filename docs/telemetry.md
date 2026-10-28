# Pipeline telemetry: OpenTelemetry → Azure Application Insights

Every script run is a trace, and every pipeline step is a span inside it, with the step's name, its
data label (synthetic, public, simulated), counts and duration. A failure is recorded on its span,
with the error type and message, and added to a failure counter. Data-quality pass rates go out as
metrics, one point per check per run. This is the record that failure detection, root-cause
assessment and recovery (the next spec) are built on. Spec 014.

Telemetry never carries note text or row-level data: names, counts, durations, rates and error
types only.

## One switch

| `DENTAL_TELEMETRY` | Where it goes | Needs |
|---|---|---|
| `off` (default) | nowhere: tests, CI, laptops | nothing |
| `console` | printed spans and metrics | nothing |
| `azure` | Application Insights, through the Azure Monitor OpenTelemetry distro | `APPLICATIONINSIGHTS_CONNECTION_STRING`; `pip install -e "python[azure]"` |
| `otlp` | any OpenTelemetry backend (self-hosted Grafana Tempo/Loki, Jaeger, SigNoz) | `OTEL_EXPORTER_OTLP_ENDPOINT`; `pip install -e "python[otlp]"` |

`azure` without a connection string logs a warning and runs with telemetry off: a missing secret
never fails a pipeline. `DENTAL_TELEMETRY_SAMPLING` (0–1, default 1.0) sets trace sampling;
`DENTAL_ENVIRONMENT` (default `dev`) is recorded on every span.

Code: `python/dental_omop_nlp/telemetry.py`. In a script, two lines:

```python
from dental_omop_nlp import telemetry
telemetry.setup()                                           # from the environment
telemetry.start_script("20_data_quality", data_label="synthetic")
with telemetry.pipeline_step("transitions", pairs=len(pairs)):   # optional finer steps
    ...
telemetry.record_value("data_quality.pass_rate", 0.97, check="cal_range")
```

Instrumented so far: `11_ai_predict.py` (every model, including the GPU encoders and MedGemma),
`20_data_quality.py` (with pass rates), `22_build_sites.py`, `37_cal_reliability.py`,
`38_nhanes_perio.py`. Databricks jobs `medgemma_reader`, `encoder_gpu` and `nhanes_perio` pass the
switch (`telemetry_exporter`, default `azure`) and read the connection string from the secret scope.

## Set up Azure (once, from your laptop)

The Azure resources are Terraform in `infra/azure/` (the azurerm provider). You need an Azure
subscription (a free account works), the Azure CLI and Terraform 1.6 or later. Sign in with
`az login`; Terraform uses that sign-in, so no token is created or copied.

```bash
export ARM_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
terraform -chdir=infra/azure init
terraform -chdir=infra/azure apply -var budget_email=you@example.com   # budget_email is optional
```

It creates, in resource group `rg-dental-omop-telemetry`:

- a Log Analytics workspace `dental-omop-nlp-logs` with a **daily cap of 0.16 GB** (31 days × 0.16
  = 4.96 GB, under the 5 GB/month free ingestion per billing account), 30-day retention;
- workspace-based Application Insights `dental-omop-nlp-appi`, **90-day retention** (included);
- optionally a 1 USD monthly budget on the resource group that emails on any actual charge.

`terraform -chdir=infra/azure destroy` removes all of it.

**State.** Terraform records what it created in `infra/azure/terraform.tfstate`. That file holds
the connection string in plain text, so it is git-ignored and stays on your laptop. To share or
automate the deployment later, move the state to an Azure Storage backend (a `backend "azurerm"`
block) rather than committing it.

Put the connection string straight into the Databricks secret scope, without printing it:

```bash
databricks secrets create-scope dental          # skip if it exists (it holds hf_token too)
databricks secrets put-secret dental appinsights_connection_string --string-value \
  "$(terraform -chdir=infra/azure output -raw connection_string)"
```

The connection string lets a holder *send* telemetry to this resource; it can't read anything. It
doesn't expire, so treat it as a secret anyway: secret scope only, never in a job parameter, a file
or chat. Stricter, later: turn off local authentication on the resource and send with a Microsoft
Entra ID identity instead.

Locally: `export DENTAL_TELEMETRY=azure APPLICATIONINSIGHTS_CONNECTION_STRING=...` in your shell
(from your password manager), then run any instrumented script.

## Staying inside the free allowance

| Guard | Where | Setting |
|---|---|---|
| Daily cap | Log Analytics workspace (Terraform) | 0.16 GB/day; ingestion stops for the day at the cap |
| Budget alert | resource group (Terraform, optional) | email on any actual charge |
| Sampling | `DENTAL_TELEMETRY_SAMPLING` | 1.0: a batch run is a few hundred spans (kilobytes), and a sampled-away failure is the one you needed. Lower it only for high-volume services |
| Log level | `telemetry.setup()` | INFO and above from the `dental_omop_nlp` logger; no DEBUG |
| Live Metrics | on | real-time view, not billed as ingestion |

How much has gone in this month (`Usage` reports MB):

```kusto
Usage
| where TimeGenerated > startofmonth(now()) and IsBillable
| summarize GB = sum(Quantity) / 1000.
```

## Queries for the questions DataOps asks

Spans the scripts send are internal spans, so in the workspace they are rows of `AppDependencies`
(`Name` = step, `Success`, `DurationMs`, attributes in `Properties`). Exceptions are in
`AppExceptions`, metrics in `AppMetrics`, log lines in `AppTraces`.

What failed this week, and how:

```kusto
AppDependencies
| where TimeGenerated > ago(7d) and Success == false
| extend step = tostring(Properties["pipeline.step"]), error = tostring(Properties["error.type"])
| summarize failures = count(), last = max(TimeGenerated) by step, error
| order by failures desc
```

Is a step getting slower:

```kusto
AppDependencies
| where TimeGenerated > ago(30d)
| summarize runs = count(), p50_s = percentile(DurationMs, 50) / 1000, p95_s = percentile(DurationMs, 95) / 1000
    by step = Name, day = bin(TimeGenerated, 1d)
| order by step asc, day asc
```

Data-quality pass rate per check over time (input for anomaly detection):

```kusto
AppMetrics
| where Name == "data_quality.pass_rate"
| extend check = tostring(Properties["check"])
| summarize pass_rate = sum(Sum) / sum(ItemCount) by check, day = bin(TimeGenerated, 1d)
```

When did each pipeline last succeed (freshness):

```kusto
AppDependencies
| where tostring(Properties["pipeline.kind"]) == "script" and Success == true
| summarize last_success = max(TimeGenerated) by script = Name
| extend hours_since = datetime_diff("hour", now(), last_success)
```

## Not yet

The pipeline doctor: classify each failure (GPU unavailable, out of memory, schema drift, data
quality, dependency), choose a recovery (retry, repair run, quarantine, escalate), notify downstream
users, and evaluate all of it on this repo's real incidents. That is the next spec; this one gives
it the record to work from.
