# Databricks notebook source
# MAGIC %md
# MAGIC # Dental notes → periodontal status: benchmark on Databricks Free Edition
# MAGIC
# MAGIC Runs the Python side of the repo end to end on serverless (CPU). Synthetic data only.
# MAGIC
# MAGIC 1. Build synthetic OMOP tables + labeled SOAP notes (no Synthea/Java needed; stand-in population)
# MAGIC 2. Patient-level split
# MAGIC 3. Baseline rungs (rules, structured, TF-IDF) — seconds
# MAGIC 4. One encoder rung (DistilBERT) — minutes on CPU at this sample size
# MAGIC 5. Optional: LLM challenger via `ai_query` on a Foundation Model endpoint
# MAGIC 6. Results and OMOP tables land as Delta in `<catalog>.<schema>` (set per target in `databricks.yml`)
# MAGIC
# MAGIC **Free Edition notes:** serverless is Python/SQL only (no R). Limited serverless GPU is
# MAGIC available from the notebook compute selector, subject to capacity and fair-use limits
# MAGIC ([Databricks, June 2026](https://www.databricks.com/blog/whats-coming-next-free-edition));
# MAGIC GPU *serving* endpoints are not. CPU is enough for this notebook. The R side of
# MAGIC this repo runs locally or in Posit against the same `labeled_notes.csv` + `split.csv`.
# MAGIC Get the repo in via *Workspace → Create → Git folder* with the public GitHub URL.

# COMMAND ----------

# MAGIC %pip install -q -e ../../python[models,track]

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os

dbutils.widgets.text("catalog", "dental_omop_perio")
dbutils.widgets.text("schema", "dental_omop_perio")
dbutils.widgets.text("n_people", "300")
dbutils.widgets.dropdown("leak_assessment", "false", ["true", "false"])
dbutils.widgets.text("experiment", "")   # set per target by the bundle (resources/mlops.yml)
catalog, schema = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalog}.{schema}.data")
os.environ["DENTAL_DATA_ROOT"] = f"/Volumes/{catalog}/{schema}/data"

# COMMAND ----------

# MAGIC %md ## 1–2. Build data and split

# COMMAND ----------

import sys
import pandas as pd
from dental_omop_nlp import paths
from dental_omop_nlp.build import build

# paths reads the env var at import time; reload after setting it.
import importlib; importlib.reload(paths)
sys.path.insert(0, str(paths.REPO_ROOT / "eval"))
from split import make_split
from score import score

labeled = build(paths.OMOP_DIR, paths.LABELS_DIR, synthea_csv=None,
                n_people=int(dbutils.widgets.get("n_people")),
                leak_assessment=dbutils.widgets.get("leak_assessment") == "true")
split = make_split(labeled)
split.to_csv(paths.LABELS_DIR / "split.csv", index=False)
df = labeled.merge(split, on="person_id")
train, test = df[df.split == "train"], df[df.split == "test"]
print(len(train), len(test))

# COMMAND ----------

# OMOP + labels as Delta, so Genie / SQL / R-via-Connect can read them.
for t in ["person", "visit_occurrence", "measurement", "note"]:
    spark.createDataFrame(pd.read_parquet(paths.OMOP_DIR / f"{t}.parquet")) \
         .write.mode("overwrite").saveAsTable(f"{catalog}.{schema}.{t}")
spark.createDataFrame(df).write.mode("overwrite").saveAsTable(f"{catalog}.{schema}.labeled_notes")
display(spark.table(f"{catalog}.{schema}.labeled_notes").limit(5))

# COMMAND ----------

# MAGIC %md ## 3–4. Ladder

# COMMAND ----------

import mlflow
from dental_omop_nlp.registry import load_registry
from dental_omop_nlp.rungs import make_rung

reg = load_registry()
mlflow.set_experiment(dbutils.widgets.get("experiment")
                      or f"/Users/{spark.sql('select current_user()').first()[0]}/dental-omop-nlp")

def run(rung_id, **kw):
    with mlflow.start_run(run_name=rung_id):
        model = make_rung(rung_id, reg, **kw).fit(train)
        pred, proba = model.predict(test)
        res = score(test["label"], pred, proba, model_id=rung_id)
        headline = res[res["class"] == ""].set_index("metric")["value"].dropna()
        mlflow.log_params({"rung": rung_id, "n_train": len(train), "n_test": len(test), **kw})
        mlflow.log_metrics(headline.to_dict())
        return res

results = [run(r) for r in ["rules_baseline", "structured_baseline", "tfidf_logreg"]]

# COMMAND ----------

# One encoder rung. CPU, so keep it small: ~600 notes x 2 epochs x 192 tokens is a few minutes.
results.append(run("distilbert-base", epochs=2, max_len=192, batch_size=16))

# COMMAND ----------

all_res = pd.concat(results)
spark.createDataFrame(all_res.astype({"value": "float"})).write.mode("append") \
     .saveAsTable(f"{catalog}.{schema}.benchmark_results")
display(all_res[all_res["class"] == ""].pivot(index="model_id", columns="metric", values="value").round(3))

# COMMAND ----------

# MAGIC %md ## 5. Optional: LLM challenger
# MAGIC Zero-shot on the test notes via a Foundation Model endpoint. Check the endpoint name under
# MAGIC *Serving* in your workspace; pay-per-token endpoints vary by region and over time.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TEMP VIEW llm_preds AS
# MAGIC SELECT note_id, label,
# MAGIC   ai_query(
# MAGIC     'databricks-meta-llama-3-3-70b-instruct',
# MAGIC     CONCAT('Classify the periodontal status in this dental SOAP note. Answer with exactly one of: ',
# MAGIC            'healthy, gingivitis, periodontitis_stage_1, periodontitis_stage_2, periodontitis_stage_3, periodontitis_stage_4.\n\n',
# MAGIC            note_text),
# MAGIC     failOnError => false
# MAGIC   ).result AS pred
# MAGIC FROM <catalog>.<schema>.labeled_notes  -- e.g. dental_omop_perio.dental_omop_perio
# MAGIC WHERE split = 'test';
# MAGIC SELECT * FROM llm_preds LIMIT 10;

# COMMAND ----------

llm = spark.table("llm_preds").toPandas()
llm["pred"] = llm["pred"].fillna("").str.strip().str.lower()
display(score(llm["label"], llm["pred"], None, model_id="llm_challenger"))
