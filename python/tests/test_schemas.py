"""Spec 022: the Databricks schemas are named for the three benches."""
import pytest

from health_transformation_lab_nlp import schemas


def test_ten_schemas_named_for_the_benches_in_the_lab_catalog():
    assert schemas.CATALOG == "health_transformation_lab"
    assert schemas.all_schemas() == [
        "landing_perio_bench", "bronze_perio_bench", "silver_perio_bench", "gold_perio_bench",
        "bronze_access_bench", "silver_access_bench", "gold_access_bench",
        "bronze_oral_health_bench", "silver_oral_health_bench", "gold_oral_health_bench"]
    assert schemas.schema("perio_bench", "gold") == "gold_perio_bench"


def test_a_bench_without_that_layer_is_refused():
    with pytest.raises(ValueError, match="access_bench has no landing"):
        schemas.schema("access_bench", "landing")
