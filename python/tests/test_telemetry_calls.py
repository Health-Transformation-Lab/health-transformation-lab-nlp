"""Spec 014 revision: every call traced with a common header (data product, environment), the way
cdh-lava-core does it with `with tracer.start_as_current_span(...)`, plus a budget so hot functions
can't flood the free allowance."""

import ast
import importlib
import inspect
import logging
from pathlib import Path

import pytest

pytest.importorskip("opentelemetry.sdk")

from dental_omop_nlp import telemetry as tm

PKG = Path(tm.__file__).parent
NOT_TRACED_MODULES = {"__init__", "paths", "telemetry"}       # telemetry can't trace itself


@pytest.fixture
def mem(monkeypatch):
    monkeypatch.setenv("DENTAL_DATA_PRODUCT_ID", "dental_omop_perio")
    exporter = tm.setup(tm.TelemetryConfig(exporter="memory", environment="dev"))
    yield exporter
    tm.setup(tm.TelemetryConfig(exporter="off"))


def test_every_span_carries_the_common_header(mem):
    with tm.trace_call("labels.label_chart"):
        pass
    (span,) = mem.get_finished_spans()
    a = span.attributes
    assert a["data_product_id"] == "dental_omop_perio" and a["environment"] == "dev"
    assert a["service.namespace"] == "dental-omop-nlp"
    assert span.resource.attributes["service.name"] == "dental_omop_perio"
    assert span.resource.attributes["service.namespace"] == "dental-omop-nlp"


def test_with_statement_gives_a_logger_that_carries_the_header(mem, caplog):
    with caplog.at_level(logging.INFO, logger="dental_omop_nlp"), tm.trace_call("study.build_study") as log:
        log.info("built %d visits", 3)
    rec = next(r for r in caplog.records if r.getMessage() == "built 3 visits")
    assert rec.data_product_id == "dental_omop_perio" and rec.environment == "dev"
    assert rec.function == "study.build_study"


def test_decorator_traces_name_module_and_errors(mem):
    @tm.traced
    def stage(x):
        """Docstring kept."""
        if x < 0:
            raise ValueError("negative CAL")
        return x * 2

    assert stage(2) == 4 and stage.__name__ == "stage" and stage.__doc__ == "Docstring kept."
    with pytest.raises(ValueError):
        stage(-1)
    ok, bad = mem.get_finished_spans()
    assert ok.attributes["code.function"] == "stage" and ok.attributes["code.namespace"] == __name__
    assert ok.name == f"{__name__.rsplit('.', 1)[-1]}.stage"
    assert not bad.status.is_ok and bad.attributes["error.type"] == "ValueError"


def test_hot_functions_stop_making_spans_after_the_budget(mem, monkeypatch):
    monkeypatch.setattr(tm, "MAX_SPANS_PER_CALLER", 3)

    @tm.traced
    def read_note(n):
        return n

    with tm.trace_call("score_all"):
        for i in range(1000):
            read_note(i)
    names = [s.name for s in mem.get_finished_spans()]
    assert names.count(f"{__name__.rsplit('.', 1)[-1]}.read_note") == 3 and names.count("score_all") == 1


def test_off_is_a_direct_call():
    tm.setup(tm.TelemetryConfig(exporter="off"))
    calls = []

    @tm.traced
    def f():
        calls.append(tm.trace.get_current_span())
        return 1

    assert f() == 1 and not calls[0].get_span_context().is_valid      # no span was opened


def _public_functions(tree):
    """Module-level functions and methods of module-level classes that run their body when called:
    not private, not generators or contextmanagers (a span would only time their creation), and not
    helpers nested inside other functions."""
    candidates = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        candidates += [n for n in cls.body if isinstance(n, ast.FunctionDef)]
    for node in candidates:
        if node.name.startswith("_"):
            continue
        decorators = {ast.unparse(d) for d in node.decorator_list}
        if "contextmanager" in decorators:
            continue
        if any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in ast.walk(node)):
            continue
        yield node, decorators


def test_every_public_function_in_the_package_is_traced():
    missing = []
    for f in sorted(PKG.glob("*.py")):
        if f.stem in NOT_TRACED_MODULES:
            continue
        for node, decorators in _public_functions(ast.parse(f.read_text())):
            if "traced" not in decorators:
                missing.append(f"{f.stem}.{node.name}")
    assert not missing, f"add @traced to: {missing}"


def test_traced_functions_still_import_and_keep_their_signatures():
    for f in sorted(PKG.glob("*.py")):
        if f.stem in NOT_TRACED_MODULES:
            continue
        try:
            mod = importlib.import_module(f"dental_omop_nlp.{f.stem}")
        except ImportError:                            # optional extras (torch, mlflow, sqlalchemy) not installed
            continue
        for name, obj in vars(mod).items():
            if inspect.isfunction(obj) and getattr(obj, "__module__", "") == mod.__name__ and hasattr(obj, "__wrapped__"):
                assert inspect.signature(obj) == inspect.signature(obj.__wrapped__), name
