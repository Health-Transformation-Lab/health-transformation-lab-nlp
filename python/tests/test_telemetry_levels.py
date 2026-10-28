"""Spec 014 revision: verbosity levels (step < call < detail), with each function's level measured by a
profiling run (calls per parent, time per call) and kept in telemetry_levels.yaml."""

from pathlib import Path

import pytest
import yaml

pytest.importorskip("opentelemetry.sdk")

from health_transformation_lab_nlp import telemetry as tm

LEVELS_FILE = Path(tm.__file__).with_name("telemetry_levels.yaml")


@pytest.fixture
def mem(monkeypatch):
    def start(level):
        monkeypatch.setenv("DENTAL_TELEMETRY_LEVEL", level)
        return tm.setup(tm.TelemetryConfig(exporter="memory"))
    yield start
    tm.setup(tm.TelemetryConfig(exporter="off"))


def _fns(monkeypatch):
    monkeypatch.setitem(tm.function_levels(), f"{__name__.rsplit('.', 1)[-1]}.hot", "detail")

    @tm.traced
    def hot(x):
        return x

    @tm.traced
    def outer():
        return sum(hot(i) for i in range(5))

    return outer


def test_default_level_skips_detail_functions(mem, monkeypatch):
    outer = _fns(monkeypatch)
    exp = mem("call")
    with tm.pipeline_step("run"):
        outer()
    names = [s.name.rsplit(".", 1)[-1] for s in exp.get_finished_spans()]
    assert "outer" in names and "run" in names and "hot" not in names


def test_detail_level_includes_them(mem, monkeypatch):
    outer = _fns(monkeypatch)
    exp = mem("detail")
    outer()
    assert any(s.name.endswith(".hot") for s in exp.get_finished_spans())


def test_step_level_keeps_only_steps_and_scripts(mem, monkeypatch):
    outer = _fns(monkeypatch)
    exp = mem("step")
    with tm.pipeline_step("run"):
        outer()
    assert [s.name for s in exp.get_finished_spans()] == ["run"]


def test_unknown_level_is_an_error(monkeypatch):
    monkeypatch.setenv("DENTAL_TELEMETRY_LEVEL", "everything")
    with pytest.raises(ValueError):
        tm.config_from_env()


def test_profile_counts_calls_per_parent_and_classify_marks_hot_and_cheap_functions(monkeypatch):
    outer = _fns(monkeypatch)
    with tm.profile() as stats:
        for _ in range(2):
            outer()
    me = __name__.rsplit(".", 1)[-1]
    assert stats[f"{me}.hot"]["calls"] == 10 and stats[f"{me}.hot"]["max_calls_per_parent"] == 5
    assert stats[f"{me}.outer"]["calls"] == 2
    levels = tm.classify(stats, max_calls_per_parent=3, min_ms=0.0)
    assert levels[f"{me}.hot"]["level"] == "detail" and levels[f"{me}.outer"]["level"] == "call"
    assert "calls per parent" in levels[f"{me}.hot"]["reason"]


def test_merge_keeps_hand_edited_levels():
    old = {"labels.label_chart": {"level": "call", "manual": True, "reason": "keep: one per chart is useful"}}
    new = {"labels.label_chart": {"level": "detail", "reason": "measured"},
           "aces.aces": {"level": "call", "reason": "measured"}}
    merged = tm.merge_levels(old, new)
    assert merged["labels.label_chart"]["level"] == "call" and merged["labels.label_chart"]["manual"]
    assert merged["aces.aces"]["level"] == "call"


def test_levels_file_is_valid_and_names_real_traced_functions():
    data = yaml.safe_load(LEVELS_FILE.read_text())
    assert data and all(v["level"] in tm.LEVELS for v in data.values())
    import importlib
    for name in data:
        module, _, qual = name.partition(".")
        obj = importlib.import_module(f"health_transformation_lab_nlp.{module}")
        for part in qual.split("."):
            obj = vars(obj).get(part, getattr(obj, part)) if isinstance(obj, type) else getattr(obj, part)
        if isinstance(obj, (staticmethod, classmethod)):
            obj = obj.__func__
        if isinstance(obj, property):
            obj = obj.fget
        assert getattr(obj, "__traced__", False), name


def test_profile_from_the_environment_is_written_at_exit(tmp_path):
    """Each pipeline runs in its own process (as in CI) and writes its profile there."""
    import json
    import subprocess
    import sys
    out = tmp_path / "profile.jsonl"
    code = ("from health_transformation_lab_nlp import labels\n"
            "for _ in range(30): labels.label_chart(labels.PerioChart(3.0, 20.0, 2.0, 10.0, 0))\n")
    env = {**__import__("os").environ, "DENTAL_TELEMETRY_PROFILE": str(out)}
    subprocess.run([sys.executable, "-c", code], env=env, check=True)
    rows = [json.loads(x) for x in out.read_text().splitlines()]
    stats = tm.merge_profiles(rows)
    assert stats["labels.label_chart"]["calls"] == 30 and stats["labels.label_chart"]["max_calls_per_parent"] == 30


def test_cal_charts_file_is_byte_identical_across_runs(tmp_path):
    import pandas as pd

    from health_transformation_lab_nlp.reliability_cal import CalParams, draw_repeated_charts, write_charts
    d = draw_repeated_charts(5, 3, 2, CalParams(), seed=1)
    a, b = tmp_path / "a.csv.gz", tmp_path / "b.csv.gz"
    write_charts(d, a)
    __import__("time").sleep(1.1)
    write_charts(d, b)
    assert a.read_bytes() == b.read_bytes() and pd.read_csv(a).equals(d.reset_index(drop=True))
