# Databricks notebook source
# MAGIC %md
# MAGIC # Migrate gold names (spec 018)
# MAGIC
# MAGIC The gold tables were renamed to the SQL conventions (AGENTS.md, "SQL and data names"): `ai_predictions` is now
# MAGIC `fact_prediction`, `gate_ok` is `is_gate_ok`, and so on (`dental_omop_nlp.gold_names`). This copies each old
# MAGIC table that still exists to its new name, columns renamed, so the MedGemma reader's Databricks rows and the
# MAGIC judge's earlier calls are kept. It runs before Load results. If a job already wrote the new table, the old rows
# MAGIC it lacks are added (by batch key), so running it again adds nothing. An old `judgments` table goes to
# MAGIC `fact_judge_call` or, if the corpus judge wrote it, `fact_corpus_judge_call`. What to do with each table is
# MAGIC `gold_names.migration_plan`. Old tables are not dropped: it prints the `DROP TABLE` statements.
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
dbutils.widgets.text("schema", "gold_perio_bench")  # noqa: F821
catalog, schema = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")  # noqa: F821


def table(name: str) -> str:
    return f"{catalog}.{schema}.{name}"


def renamed(old: str, new: str):
    """The old table under new's column names, _count columns as bigint. A value the cast can't keep fails
    instead of turning into null."""
    names = gold_names.TABLES[new]
    sdf = spark.table(table(old))  # noqa: F821
    sdf = sdf.withColumnsRenamed({c: names[c] for c in sdf.columns if c in names})
    counts = [c for c in sdf.columns if c.endswith("_count") and not c.startswith("avg_")]
    if counts:
        nulls = sdf.select([F.count(F.when(F.col(c).isNull(), 1)).alias(c) for c in counts]).first()
        cast = sdf.select([F.col(c).cast("bigint") for c in counts])
        after = cast.select([F.count(F.when(F.col(c).isNull(), 1)).alias(c) for c in counts]).first()
        bad = [c for c in counts if after[c] != nulls[c]]
        if bad:
            raise ValueError(f"{old}: {bad} hold values that aren't whole numbers; fix them before migrating")
        for c in counts:
            sdf = sdf.withColumn(c, F.col(c).cast("bigint"))
    return sdf


def rows(name: str) -> int:
    return spark.table(table(name)).count()  # noqa: F821


# Which old tables exist, with their columns; the decision is gold_names.migration_plan (tested).
existing = {t.name: spark.table(table(t.name)).columns  # noqa: F821
            for t in spark.catalog.listTables(f"{catalog}.{schema}")  # noqa: F821
            if t.name in gold_names.RENAMED or t.name in gold_names.TABLES}
plan = gold_names.migration_plan(existing)
failed = [f"{old}: no gold name for column(s) {cols}" for action, old, cols in plan if action == "fail"]
if failed:
    raise ValueError("add them to dental_omop_nlp/gold_names.py first: " + "; ".join(failed))

for action, old, new in plan:
    if action == "copy":
        renamed(old, new).write.mode("overwrite").saveAsTable(table(new))
        if rows(new) != rows(old):
            raise RuntimeError(f"{old} -> {new}: row counts differ ({rows(old)} vs {rows(new)})")
    elif action == "rewrite":       # same name, old columns: Delta overwrites from the snapshot it read
        n = rows(old)
        renamed(old, new).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(table(new))
        if rows(new) != n:
            raise RuntimeError(f"{old}: row counts differ after renaming its columns ({n} vs {rows(new)})")
    elif action == "merge":         # a job wrote the new table first: add the old rows whose batch key it lacks
        key = gold_names.MERGE_KEYS[new]
        current = spark.table(table(new)).select(*key).distinct()  # noqa: F821
        src = renamed(old, new)
        cond = [src[k].eqNullSafe(current[k]) for k in key]
        missing = src.join(current, cond, "left_anti")
        missing.write.mode("append").option("mergeSchema", "true").saveAsTable(table(new))
    print(f"{action}: {old} -> {new}" + ("" if action != "stale" else " (the new table is rebuilt each run; old copy left)"))

drops = [f"DROP TABLE {table(old)};" for _, old, new in plan if old != new]
print("migrated:", "nothing to do" if not plan else len(plan))
if drops:
    print("Old tables left in place. After checking the new ones, drop them with:\n" + "\n".join(drops))
