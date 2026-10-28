"""Spec 021: the Databricks schemas are named for the three benches, and the old perio schemas carry over."""
from dental_omop_nlp import schemas


def test_eleven_schemas_named_for_the_benches():
    assert schemas.CATALOG == "dental_omop"
    assert schemas.all_schemas() == [
        "landing_perio_bench", "bronze_perio_bench", "silver_perio_bench", "gold_perio_bench",
        "bronze_access_bench", "silver_access_bench", "gold_access_bench",
        "bronze_oral_health_bench", "silver_oral_health_bench", "gold_oral_health_bench"]
    assert schemas.schema("perio_bench", "gold") == "gold_perio_bench"


def test_each_old_perio_layer_moves_to_its_perio_bench_layer():
    assert schemas.MOVES == {"landing_dental_omop_perio": "landing_perio_bench",
                             "bronze_dental_omop_perio": "bronze_perio_bench",
                             "silver_dental_omop_perio": "silver_perio_bench",
                             "gold_dental_omop_perio": "gold_perio_bench"}


def test_plan_copies_tables_the_new_schema_lacks_and_skips_the_rest():
    existing = {"gold_dental_omop_perio": {"fact_prediction", "dim_result_file"},
                "gold_perio_bench": {"dim_result_file"},
                "bronze_dental_omop_perio": set()}
    assert schemas.migration_plan(existing) == [
        ("skip", "gold_dental_omop_perio", "gold_perio_bench", "dim_result_file"),
        ("copy", "gold_dental_omop_perio", "gold_perio_bench", "fact_prediction")]


def test_plan_is_empty_where_the_old_schemas_never_existed():
    assert schemas.migration_plan({"gold_perio_bench": {"fact_prediction"}}) == []
    assert schemas.migration_plan({}) == []


def test_plan_copies_into_a_new_schema_that_has_no_tables_yet():
    assert schemas.migration_plan({"silver_dental_omop_perio": {"t"}}) == [
        ("copy", "silver_dental_omop_perio", "silver_perio_bench", "t")]


def test_model_versions_already_copied_are_skipped():
    assert schemas.versions_to_copy([3, 1, 2], copied_from={2}) == [1, 3]
    assert schemas.versions_to_copy([1], copied_from={1}) == []


def test_volume_files_already_copied_are_skipped():
    assert schemas.files_to_copy({"logs/a.log", "nhanes/x.csv"}, {"logs/a.log"}) == ["nhanes/x.csv"]
