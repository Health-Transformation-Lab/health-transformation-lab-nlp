"""Spec 029: the API serves the registry and each report, and fails clearly."""

import pytest
from fastapi.testclient import TestClient

from bench_report import sources
from bench_report.main import create_app


@pytest.fixture(scope="module")
def client(fixture_settings, fixture_source):
    with TestClient(create_app(fixture_settings, fixture_source)) as c:
        yield c


def test_health_names_the_source(client):
    assert client.get("/api/health").json() == {"ok": True, "source": "fixtures",
                                                "catalog": "health_transformation_lab"}


def test_benches_list_every_bench_with_its_reports(client):
    b = client.get("/api/benches").json()
    assert [x["name"] for x in b] == ["PerioBench", "OralHealthBench", "AccessBench"]
    assert b[0]["reports"][0]["key"] == "dq" and b[1]["reports"] == []


def test_the_dq_report_is_served_then_cached(client):
    first = client.get("/api/benches/perio_bench/reports/dq")
    assert first.status_code == 200
    body = first.json()
    assert body["synthetic"] is True and body["gold_schema"] == "health_transformation_lab.gold_perio_bench"
    assert body["bench_name"] == "PerioBench" and body["tiles"]["All"]["completeness"]["value"] > 0
    assert client.get("/api/benches/perio_bench/reports/dq").json()["cached"] is True


@pytest.mark.parametrize("path, says", [("/api/benches/nope/reports/dq", "no bench"),
                                        ("/api/benches/perio_bench/reports/nope", "no report"),
                                        ("/api/benches/access_bench/reports/dq", "exploratory")])
def test_unknown_benches_and_reports_are_404_with_a_reason(client, path, says):
    r = client.get(path)
    assert r.status_code == 404 and says in r.json()["detail"]


class _Failing:
    def check(self):
        pass

    def query(self, sql):
        raise sources.QueryError("statement 01 FAILED: TABLE_OR_VIEW_NOT_FOUND")


def test_a_failed_query_is_a_502_that_says_why(fixture_settings):
    with TestClient(create_app(fixture_settings, _Failing())) as c:
        r = c.get("/api/benches/perio_bench/reports/dq")
    assert r.status_code == 502 and "TABLE_OR_VIEW_NOT_FOUND" in r.json()["detail"]


class _Unreachable(_Failing):
    def check(self):
        raise sources.QueryError("cannot reach SQL warehouse")


def test_the_app_does_not_start_when_the_warehouse_check_fails(fixture_settings):
    with pytest.raises(sources.QueryError, match="cannot reach"):
        with TestClient(create_app(fixture_settings, _Unreachable())):
            pass
