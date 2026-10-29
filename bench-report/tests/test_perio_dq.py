"""Spec 029 US1: the DQ report's measures, run on the snapshot of the gold tables, match the same measures counted
straight from the snapshot's CSVs, and the dashboard's definitions (spec 019 US2)."""

import csv
from pathlib import Path

import pytest

from bench_report.reports import perio_dq

from .conftest import GOLD

FIX = Path(__file__).parent / "fixtures" / "gold_perio_bench"


def _csv(table):
    with open(FIX / f"{table}.csv") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def payload(fixture_source):
    return perio_dq.REPORT.run(fixture_source, GOLD)


def test_every_query_returns_rows(fixture_source):
    for name, sql in perio_dq.SQL.items():
        assert fixture_source.query(sql.replace("{gold}", GOLD)), name


def test_the_sql_reads_only_the_tables_the_report_declares():
    text = " ".join(perio_dq.SQL.values())
    for table in perio_dq.TABLES:
        assert f"{{gold}}.{table}" in text
    assert text.count("{gold}.") == sum(text.count(f"{{gold}}.{t}") for t in perio_dq.TABLES)


def test_completeness_and_accuracy_tiles_count_the_visits(payload):
    visits = _csv("fact_visit_evidence")
    complete = [v for v in visits if "unknown" not in (v["exam_form_status_code"], v["dx_completed_status_code"],
                                                       v["probing_chart_status_code"])]
    agree = [v for v in visits if v["rules_v0_status_code"] == v["truth_status_code"]]
    tiles = payload["tiles"]["All"]
    assert tiles["completeness"]["value"] == round(100 * len(complete) / len(visits), 1)
    assert tiles["accuracy"]["value"] == round(100 * len(agree) / len(visits), 1)
    one = [v for v in visits if v["clinic_code"] == "1"]
    assert payload["tiles"]["1"]["completeness"]["value"] == round(
        100 * sum(v in complete for v in one) / len(one), 1)


def test_consistency_is_the_spread_of_clinic_prevalence_and_temporal_the_design_rules_improved_share(payload):
    prev = [float(p["periodontitis_ratio"]) for p in _csv("dq_prevalence")
            if p["level_code"] == "clinic" and p["method_name"] == "algorithm_design"]
    assert payload["tiles"]["All"]["consistency"]["value"] == round(100 * max(prev) - 100 * min(prev), 1)
    design = next(t for t in _csv("dq_temporal_change") if t["method_name"] == "algorithm_design")
    assert payload["tiles"]["All"]["temporal"]["value"] == round(100 * float(design["better_ratio"]), 1)


def test_reliability_is_not_assessed_and_the_payload_says_synthetic(payload):
    assert payload["synthetic"] is True
    assert payload["tiles"]["All"]["reliability"] == {"value": None, "unit": "", "status": "none", "scope": "All"}


def test_every_clinic_has_tiles_and_all_comes_first(payload):
    assert payload["clinics"][0] == "All" and payload["clinics"][1:] == [str(i) for i in range(1, 9)]
    assert set(payload["tiles"]) == set(payload["clinics"])


def test_agreement_counts_only_the_visits_a_source_answers(payload):
    visits = _csv("fact_visit_evidence")
    answered = [v for v in visits if v["note_status_code"] != "unknown"]
    row = next(a for a in payload["accuracy"] if a["clinic"] == "All" and a["source"] == "notes")
    assert row["answered_pct"] == round(100 * len(answered) / len(visits), 1)
    assert row["agree_pct"] == round(100 * sum(v["note_status_code"] == v["truth_status_code"]
                                                for v in answered) / len(answered), 1)


def test_the_transition_matrix_is_in_stage_order_and_improvement_is_below_the_diagonal(payload):
    t = payload["transitions"]
    assert t["stages"] == list(perio_dq.STATUS_LABELS)
    for i, row in enumerate(t["direction"]):
        for j, d in enumerate(row):
            assert d == ("better" if j < i else "same" if j == i else "worse")
    for row in t["row_pct"]:
        assert sum(row) == pytest.approx(100, abs=0.5)


def test_concordance_is_symmetric_with_no_diagonal(payload):
    m = payload["concordance"]["agree_pct"]
    for i in range(len(m)):
        assert m[i][i] is None
        for j in range(len(m)):
            assert m[i][j] == m[j][i]


@pytest.mark.parametrize("domain, value, expected", [
    ("completeness", 95, "good"), ("completeness", 80, "warn"), ("completeness", 46.4, "crit"),
    ("consistency", 5, "good"), ("consistency", 14.5, "warn"), ("consistency", 20, "crit"),
    ("temporal", None, "none")])
def test_status_pills_follow_the_thresholds(domain, value, expected):
    assert perio_dq.status(domain, value) == expected
