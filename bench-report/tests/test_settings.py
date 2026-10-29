"""Spec 029 US3: every setting is checked at start; a bad one fails naming it (AGENTS.md "Configuration")."""

import pytest

from bench_report.settings import SettingsError, load

OK = {"DATABRICKS_HOST": "https://adb-1.azuredatabricks.net", "DATABRICKS_WAREHOUSE_ID": "20e58799ac61f0da"}


def test_databricks_settings_load_with_the_shared_defaults():
    s = load(OK)
    assert (s.source, s.catalog, s.cache_seconds, s.warehouse_id) == ("databricks", "health_transformation_lab", 300,
                                                                      "20e58799ac61f0da")


def test_a_host_without_a_scheme_gets_https():
    assert load({**OK, "DATABRICKS_HOST": "adb-1.azuredatabricks.net/"}).host == "https://adb-1.azuredatabricks.net"


@pytest.mark.parametrize("env, named", [
    ({"DATABRICKS_WAREHOUSE_ID": "20e58799ac61f0da"}, "DATABRICKS_HOST"),
    ({**OK, "DATABRICKS_HOST": "http://adb-1.net"}, "DATABRICKS_HOST"),
    ({"DATABRICKS_HOST": OK["DATABRICKS_HOST"]}, "DATABRICKS_WAREHOUSE_ID"),
    ({**OK, "DATABRICKS_WAREHOUSE_ID": "/sql/1.0/warehouses/20e58799ac61f0da"}, "DATABRICKS_WAREHOUSE_ID"),
    ({**OK, "BENCH_REPORT_SOURCE": "postgres"}, "BENCH_REPORT_SOURCE"),
    ({**OK, "BENCH_REPORT_CATALOG": "Dev-Catalog"}, "BENCH_REPORT_CATALOG"),
    ({**OK, "BENCH_REPORT_CACHE_SECONDS": "five"}, "BENCH_REPORT_CACHE_SECONDS"),
    ({"BENCH_REPORT_SOURCE": "fixtures", "BENCH_REPORT_FIXTURES_DIR": "/no/such/folder"}, "BENCH_REPORT_FIXTURES_DIR"),
])
def test_a_missing_or_malformed_setting_fails_naming_it(env, named):
    with pytest.raises(SettingsError, match=named):
        load(env)


def test_fixtures_need_no_workspace_settings():
    s = load({"BENCH_REPORT_SOURCE": "fixtures"})
    assert s.host is None and s.fixtures_dir.is_dir()
