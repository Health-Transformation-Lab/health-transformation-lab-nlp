# Databricks notebook source
# MAGIC %md
# MAGIC # Migrate gold names (spec 018)
# MAGIC
# MAGIC The gold tables were renamed to the SQL conventions (AGENTS.md, "SQL and data names"): `ai_predictions` is now
# MAGIC `fact_prediction`, `gate_ok` is `is_gate_ok`, and so on (`dental_omop_nlp.gold_names`). This copies each old
# MAGIC table that still exists to its new name, columns renamed, so the MedGemma reader's Databricks rows and the
# MAGIC judge's earlier calls are kept. It runs before Load results; once a new table exists it is skipped, so running
# MAGIC it again does nothing. Old tables are not dropped: it prints the `DROP TABLE` statements to run after checking.
# MAGIC Synthetic data only. Serverless CPU.

# COMMAND ----------

# MAGIC %pip install -q -e ../../python

# COMMAND ----------

dbutils.library.restartPython()  # noqa: F821

# COMMAND ----------

from dental_omop_nlp import gold_names, tracking
from pyspark.sql import functions as F

dbutils.widgets.text("git_commit", "")  # noqa: F821  set by the job: the commit it was deployed from
tracking.use_git_commit(dbutils)  # noqa: F821
dbutils.widgets.text("catalog", "dental_omop")  # noqa: F821
dbutils.widgets.text("schema", "gold_dental_omop_perio")  # noqa: F821
catalog, schema = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")  # noqa: F821


def table(name: str) -> str:
    return f"{catalog}.{schema}.{name}"


def renamed(old: str, new: str):
    """The old table under the new column names, _count columns as bigint. A column the mapping doesn't know stops
    the migration, naming it: it needs a gold name in gold_names.py first."""
    names = gold_names.TABLES[new]
    sdf = spark.table(table(old))  # noqa: F821
    unknown = [c for c in sdf.columns if c not in names and c not in names.values()]
    if unknown:
        raise ValueError(f"{old}: no gold name for column(s) {unknown}; add them to dental_omop_nlp/gold_names.py")
    sdf = sdf.withColumnsRenamed({c: names[c] for c in sdf.columns if c in names})
    for c in sdf.columns:
        if c.endswith("_count") and not c.startswith("avg_"):
            sdf = sdf.withColumn(c, F.col(c).cast("bigint"))
    return sdf


done, drops = [], []
for old, new in gold_names.RENAMED.items():
    if not spark.catalog.tableExists(table(old)):  # noqa: F821
        continue
    if old == new:          # same name, new columns: rewrite in place unless it already has them
        if set(spark.table(table(old)).columns) <= set(gold_names.TABLES[new].values()):  # noqa: F821
            continue
        renamed(old, new).localCheckpoint().write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(table(new))
        done.append(f"{old} (columns renamed)")
        continue
    if not spark.catalog.tableExists(table(new)):  # noqa: F821
        renamed(old, new).write.mode("overwrite").saveAsTable(table(new))
        done.append(f"{old} -> {new}")
    drops.append(f"DROP TABLE {table(old)};")

print("migrated:", done or "nothing to do")
if drops:
    print("Old tables left in place. After checking the new ones, drop them with:\n" + "\n".join(drops))
