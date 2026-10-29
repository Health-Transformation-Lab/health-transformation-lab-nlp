import pytest

from bench_report import settings, sources

GOLD = "health_transformation_lab.gold_perio_bench"


@pytest.fixture(scope="session")
def fixture_settings():
    return settings.load({"BENCH_REPORT_SOURCE": "fixtures"})


@pytest.fixture(scope="session")
def fixture_source(fixture_settings):
    return sources.FixtureSource(fixture_settings)
