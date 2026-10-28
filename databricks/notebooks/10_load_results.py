# Databricks notebook source
# MAGIC %md
# MAGIC # Load results: every committed model result into the gold tables (spec 016)
# MAGIC
# MAGIC Model answers on the 240 synthetic review notes are made in three places: Databricks jobs (which
# MAGIC write their own tables), Kaggle's free GPU (collected into a pull request by the `kaggle-medgemma`
# MAGIC workflow) and laptops. Whatever is committed under `data/datasets/` is deployed with the bundle;
# MAGIC this job, run after every deploy, appends each file version it hasn't seen yet:
# MAGIC
# MAGIC - `result_files`: one row per file version (SHA-256), with its source (`kaggle`, `repo`) and run URL
# MAGIC - `ai_predictions`: method, visit_id, predicted status
# MAGIC - `llm_reader_runs`: the LLM reader details, next to the rows the MedGemma reader job writes
# MAGIC   (`source = databricks`)
# MAGIC
# MAGIC and logs one MLflow run per new LLM file. Running it again adds nothing. `simulated_*` files are
# MAGIC never loaded. Serverless CPU.

# COMMAND ----------

# MAGIC %pip install -q -e ../../python[track]

# COMMAND ----------

dbutils.library.restartPython()  # noqa: F821

# COMMAND ----------

import os

import pandas as pd
from dental_omop_nlp import results_store, tracking
from dental_omop_nlp.paths import DATASETS_DIR
from pyspark.sql import functions as F

dbutils.widgets.text("git_commit", "")  # noqa: F821  set by the job: the commit it was deployed from
commit = tracking.use_git_commit(dbutils)  # noqa: F821
dbutils.widgets.text("catalog", "dental_omop")  # noqa: F821
dbutils.widgets.text("schema", "gold_dental_omop_perio")  # noqa: F821
dbutils.widgets.text("experiment_name", "")  # noqa: F821  the bundle's experiment; empty: no MLflow runs
catalog, schema = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")  # noqa: F821
experiment = dbutils.widgets.get("experiment_name")  # noqa: F821


def table(name: str) -> str:
    return f"{catalog}.{schema}.{name}"


# COMMAND ----------

files = results_store.result_files(DATASETS_DIR)
loaded = set()
if spark.catalog.tableExists(table("result_files")):  # noqa: F821
    loaded = {r.sha256 for r in spark.table(table("result_files")).select("sha256").collect()}  # noqa: F821
new = results_store.new_files(files, loaded)
print(f"{len(files)} result files deployed, {len(new)} new or changed")
display(new)  # noqa: F821

# COMMAND ----------

now = pd.Timestamp.now(tz="UTC")


def append(df: pd.DataFrame, name: str):
    """Append, with each column cast to the type the table already has (an empty `error` column is text in one
    file and a number in another); new columns are added (mergeSchema)."""
    if not len(df):
        return
    df = df.astype({c: "string" for c in df.columns if df[c].isna().all()})   # an empty column is text, not void
    sdf = spark.createDataFrame(df.assign(git_commit=commit, loaded_at=now))  # noqa: F821
    if spark.catalog.tableExists(table(name)):  # noqa: F821
        for field in spark.table(table(name)).schema:  # noqa: F821
            if field.name in sdf.columns:
                sdf = sdf.withColumn(field.name, F.col(field.name).cast(field.dataType))
    sdf.write.mode("append").option("mergeSchema", "true").saveAsTable(table(name))


preds = new[new.kind == "predictions"]
details = new[new.kind == "llm_details"]
append(results_store.prediction_rows(preds, DATASETS_DIR), "ai_predictions")
append(results_store.detail_rows(details, DATASETS_DIR).assign(run_ts=now), "llm_reader_runs")
append(new, "result_files")              # last: a failure above leaves these versions to load next time

# COMMAND ----------

# One MLflow run per new LLM file, in the bundle's experiment. Tracking never fails the job.
if experiment and len(details):
    os.environ["MLFLOW_TRACKING_URI"] = "databricks"
    os.environ["DENTAL_MLFLOW_EXPERIMENT"] = experiment
    truth = pd.read_csv(DATASETS_DIR / "answer_key" / "review_key.csv").set_index("visit_id").truth_status
    for f in details.itertuples():
        d = pd.read_csv(DATASETS_DIR / f.file)
        first = d.iloc[0]
        params = {"method": f.method, "source": f.source, "run_url": f.run_url, "file_sha256": f.sha256,
                  "prompt_version": first.get("prompt_version", ""), "shots": first.get("shots", "")}
        with tracking.track("load_results", f"{f.method} ({f.source})", params=params) as run:
            run.log_metrics(results_store.llm_run_metrics(d, truth))

print("loaded:", list(new.file) or "nothing new")
