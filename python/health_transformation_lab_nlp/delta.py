"""Idempotent Delta writes from notebooks: delete-then-append by batch key (AGENTS.md, docs/operations.md).

    replace_batch(spark, rows, "health_transformation_lab.gold_health_transformation_lab.fact_prediction",
                  {"source_code": "databricks", "run_id": run_id, "method_name": method})

A retry of the same batch replaces its rows instead of adding them again. Rows carry the key columns, so a bad
batch can be found and removed. Rows written by other writers are untouched: their key columns are NULL or
differ (Load results keys on file_sha256 and leaves source_code = databricks rows alone).
"""

from __future__ import annotations

import re

import pandas as pd

from .telemetry import traced

_SAFE = re.compile(r"[\w.:+@/-]+")


@traced
def replace_batch(spark, rows: pd.DataFrame, table: str, key: dict) -> int:
    """Delete table's rows with these key values, then append rows (with the key columns set). New columns are
    added (mergeSchema); a column that is empty in this batch takes the table's type, or string in a new table
    (an all-null `error` would otherwise read as a number). Returns the rows written."""
    for k, v in key.items():
        if not re.fullmatch(r"\w+", k) or not _SAFE.fullmatch(str(v)):
            raise ValueError(f"batch key {k}={v!r}: letters, digits and . : + @ / - _ only")
    rows = rows.assign(**{k: str(v) for k, v in key.items()})
    empty = [c for c in rows.columns if rows[c].isna().all()]
    sdf = spark.createDataFrame(rows.astype({c: "string" for c in empty}))
    if spark.catalog.tableExists(table):
        schema = spark.table(table).schema
        if set(key) <= set(schema.fieldNames()):        # a table without the key columns has no rows of this batch
            where = " AND ".join(f"{k} = '{v}'" for k, v in key.items())
            spark.sql(f"DELETE FROM {table} WHERE {where}")
        for field in schema.fields:
            if field.name in empty:
                sdf = sdf.withColumn(field.name, sdf[field.name].cast(field.dataType))
    sdf.write.mode("append").option("mergeSchema", "true").saveAsTable(table)
    return len(rows)
