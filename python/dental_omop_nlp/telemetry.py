"""Pipeline telemetry with OpenTelemetry (spec 014).

One switch, `DENTAL_TELEMETRY`, picks where traces, metrics and logs go:

    off      default: nothing leaves the process (tests, CI, laptops)
    console  print spans and metrics (debugging)
    azure    Azure Application Insights through the Azure Monitor OpenTelemetry distro;
             needs APPLICATIONINSIGHTS_CONNECTION_STRING (Databricks: secret scope `dental`,
             key `appinsights_connection_string`). Without it: a warning, then off.
    otlp     any OpenTelemetry backend over OTLP (self-hosted Grafana Tempo/Loki, Jaeger, SigNoz);
             OTEL_EXPORTER_OTLP_ENDPOINT as usual
    memory   in-process, for tests

Cost guards for the Azure free allowance (5 GB/month per billing account): the workspace daily cap
in infra/azure/main.tf (Terraform), `DENTAL_TELEMETRY_SAMPLING` (default 1.0: a batch run is a few hundred
spans, and a sampled-away failure is the one you needed), and only INFO and above from the package
logger. Telemetry never carries note text or row-level data: step names, counts, durations, rates
and error types only.

    from dental_omop_nlp import telemetry
    telemetry.setup()                                   # from the environment
    with telemetry.pipeline_step("build_sites", data_label="synthetic", rows=len(v)):
        ...
    telemetry.record_value("data_quality.pass_rate", 0.97, check="cal_range")
"""

from __future__ import annotations

import atexit
import logging
import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import ClassVar

from opentelemetry import context, metrics, trace
from opentelemetry.trace import Status, StatusCode

SERVICE = "dental-omop-nlp"
LOGGER = "dental_omop_nlp"
EXPORTERS = ("off", "console", "azure", "otlp", "memory")
log = logging.getLogger(LOGGER)


@dataclass(frozen=True)
class TelemetryConfig:
    exporter: str = "off"
    connection_string: str = field(default="", repr=False)
    sampling_ratio: float = 1.0
    environment: str = "dev"

    def __post_init__(self):
        if self.exporter not in EXPORTERS:
            raise ValueError(f"DENTAL_TELEMETRY must be one of {EXPORTERS}")
        if not 0.0 <= self.sampling_ratio <= 1.0:
            raise ValueError("DENTAL_TELEMETRY_SAMPLING must be between 0 and 1")


def _clean(value: str) -> str:
    """Strip what shells and copy-paste add: whitespace, Windows line endings, surrounding quotes."""
    return value.strip().strip("\"'").strip()


def _looks_valid(connection_string: str) -> bool:
    """key=value pairs separated by ';', one of them InstrumentationKey (the Azure Monitor format)."""
    pairs = [p.split("=", 1) for p in connection_string.split(";") if p.strip()]
    return all(len(p) == 2 for p in pairs) and any(k.strip().lower() == "instrumentationkey" for k, _ in pairs)


def config_from_env() -> TelemetryConfig:
    return TelemetryConfig(exporter=os.environ.get("DENTAL_TELEMETRY", "off").strip().lower() or "off",
                           connection_string=_clean(os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", "")),
                           sampling_ratio=float(os.environ.get("DENTAL_TELEMETRY_SAMPLING", "1.0")),
                           environment=os.environ.get("DENTAL_ENVIRONMENT", "dev"))


class _State:
    exporter = "off"
    tracer: trace.Tracer = trace.NoOpTracer()
    meter: metrics.Meter = metrics.NoOpMeter(SERVICE)
    instruments: ClassVar[dict] = {}
    script = None


def _resource(c: TelemetryConfig):
    from opentelemetry.sdk.resources import Resource
    return Resource.create({"service.name": SERVICE, "deployment.environment": c.environment})


def _sdk_providers(c: TelemetryConfig, span_exporter, metric_exporter):
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
    from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

    tp = TracerProvider(resource=_resource(c), sampler=ParentBased(TraceIdRatioBased(c.sampling_ratio)))
    simple = c.exporter in ("memory", "console")
    tp.add_span_processor((SimpleSpanProcessor if simple else BatchSpanProcessor)(span_exporter))
    readers = [PeriodicExportingMetricReader(metric_exporter)] if metric_exporter is not None else []
    return tp.get_tracer(SERVICE), MeterProvider(resource=_resource(c), metric_readers=readers).get_meter(SERVICE)


def setup(config: TelemetryConfig | None = None):
    """Configure telemetry. Returns the in-memory span exporter for exporter='memory', else None."""
    c = config or config_from_env()
    _State.instruments = {}
    logging.getLogger(LOGGER).setLevel(logging.INFO)
    out = None
    if c.exporter == "azure" and not c.connection_string:
        log.warning("DENTAL_TELEMETRY=azure but APPLICATIONINSIGHTS_CONNECTION_STRING is not set: telemetry off")
        c = TelemetryConfig(exporter="off")
    elif c.exporter == "azure" and not _looks_valid(c.connection_string):   # never log the value itself
        log.warning("APPLICATIONINSIGHTS_CONNECTION_STRING is not a valid Application Insights connection "
                    "string (expected InstrumentationKey=...;IngestionEndpoint=...): telemetry off")
        c = TelemetryConfig(exporter="off")
    if c.exporter == "off":
        _State.tracer, _State.meter = trace.NoOpTracer(), metrics.NoOpMeter(SERVICE)
    elif c.exporter == "memory":
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
        out = InMemorySpanExporter()
        _State.tracer, _State.meter = _sdk_providers(c, out, None)
    elif c.exporter == "console":
        from opentelemetry.sdk.metrics.export import ConsoleMetricExporter
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter
        _State.tracer, _State.meter = _sdk_providers(c, ConsoleSpanExporter(), ConsoleMetricExporter())
    elif c.exporter == "otlp":
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        _State.tracer, _State.meter = _sdk_providers(c, OTLPSpanExporter(), OTLPMetricExporter())
    else:                                                      # azure
        from azure.monitor.opentelemetry import configure_azure_monitor
        configure_azure_monitor(connection_string=c.connection_string, sampling_ratio=c.sampling_ratio,
                                enable_live_metrics=True, logger_name=LOGGER, resource=_resource(c))
        _State.tracer, _State.meter = trace.get_tracer(SERVICE), metrics.get_meter(SERVICE)
    _State.exporter = c.exporter
    return out


def active_exporter() -> str:
    return _State.exporter


def _instrument(kind: str, name: str, unit: str = ""):
    key = (kind, name)
    if key not in _State.instruments:
        make = {"histogram": _State.meter.create_histogram, "counter": _State.meter.create_counter}[kind]
        _State.instruments[key] = make(name, unit=unit)
    return _State.instruments[key]


def record_value(name: str, value: float, **attrs) -> None:
    """A measured value (pass rate, rows, AUROC) as a histogram point with attributes."""
    _instrument("histogram", name).record(value, attributes=attrs)


def _record_failure(span, name: str, e: BaseException) -> None:
    span.set_attribute("error.type", type(e).__name__)
    span.record_exception(e)
    span.set_status(Status(StatusCode.ERROR, str(e)[:500]))
    _instrument("counter", "pipeline.step.failures").add(1, {"pipeline.step": name, "error.type": type(e).__name__})
    log.error("step %s failed: %s: %s", name, type(e).__name__, str(e)[:500])


@contextmanager
def pipeline_step(name: str, **attrs):
    """A span for one pipeline step; on failure the error is recorded, counted and re-raised."""
    base = {"pipeline.step": name, **{("data.label" if k == "data_label" else k): v for k, v in attrs.items()}}
    start = time.perf_counter()
    with _State.tracer.start_as_current_span(name, attributes=base, record_exception=False,
                                             set_status_on_exception=False) as span:
        try:
            yield span
        except Exception as e:
            _record_failure(span, name, e)
            raise
        finally:
            _instrument("histogram", "pipeline.step.duration", "s").record(
                time.perf_counter() - start, {"pipeline.step": name})


def start_script(name: str, **attrs) -> None:
    """One call at the top of a script: a run-level span that every pipeline_step nests under, ended at
    exit; an uncaught error is recorded on it (through sys.excepthook) before Python prints it."""
    end_script()
    span = _State.tracer.start_span(name, attributes={"pipeline.step": name, "pipeline.kind": "script",
                                                      **{("data.label" if k == "data_label" else k): v
                                                         for k, v in attrs.items()}})
    token = context.attach(trace.set_span_in_context(span))
    prev = sys.excepthook

    def hook(etype, value, tb):
        if _State.script is not None and _State.script[0] is span:
            _record_failure(span, name, value)
            end_script()
        prev(etype, value, tb)

    _State.script = (span, token, prev, time.perf_counter(), name)
    sys.excepthook = hook
    atexit.register(end_script)


def end_script() -> None:
    """End the run span (idempotent) and put the previous excepthook back."""
    if _State.script is None:
        return
    span, token, prev, start, name = _State.script
    _State.script = None
    sys.excepthook = prev
    _instrument("histogram", "pipeline.step.duration", "s").record(time.perf_counter() - start,
                                                                   {"pipeline.step": name})
    span.end()
    context.detach(token)      # OpenTelemetry logs, never raises, if the context already moved on


def use_databricks_secret(dbutils, exporter: str = "azure", scope: str = "dental",
                          key: str = "appinsights_connection_string") -> str:
    """In a Databricks notebook: put the telemetry settings in the environment, where the scripts the
    notebook starts pick them up. A missing secret turns telemetry off; it never fails the job."""
    if exporter == "azure":
        try:
            os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"] = _clean(dbutils.secrets.get(scope, key))
        except Exception as e:  # noqa: BLE001  dbutils raises its own exception types
            log.warning("no secret %s/%s (%s): telemetry off", scope, key, type(e).__name__)
            exporter = "off"
    os.environ["DENTAL_TELEMETRY"] = exporter
    return exporter
