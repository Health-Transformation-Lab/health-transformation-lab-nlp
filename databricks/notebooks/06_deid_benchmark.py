# Databricks notebook source
# MAGIC %md
# MAGIC # De-identification benchmark, including the AI methods (spec 007)
# MAGIC
# MAGIC Runs `python/scripts/26_deid_benchmark.py` where the AI engines can reach their models:
# MAGIC
# MAGIC | Engine | What | Needs |
# MAGIC |---|---|---|
# MAGIC | `hf_stanford` | StanfordAIMI/stanford-deidentifier-base (transformer, MIT) | Hugging Face download; GPU compute is faster |
# MAGIC | `hf_obi` | obi/deid_roberta_i2b2 (RoBERTa on i2b2 2014, MIT) | same |
# MAGIC | `llm` | an LLM listing identifiers verbatim | a Databricks serving endpoint (OpenAI-compatible) |
# MAGIC | `ai_mask` | Databricks SQL AI Function `ai_mask` (Public Preview): masks the listed entity types | a serverless or Pro SQL warehouse in a region with AI Functions |
# MAGIC | `presidio` | spaCy NER + recognizers | `presidio-analyzer` and a spaCy model |
# MAGIC | `regex`, `regex_v2` | patterns | nothing |
# MAGIC
# MAGIC Synthetic, labeled fake PHI only: the challenge set is generated here, never real notes.

# COMMAND ----------

# MAGIC %pip install -q -e ../../python[models] presidio-analyzer https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("llm_endpoint", "")   # e.g. a pay-per-token Foundation Model endpoint name
dbutils.widgets.text("sql_warehouse_id", "")   # for ai_mask
dbutils.widgets.text("engines", "regex,regex_v2+guard,presidio+regex_v2+guard,hf_stanford,hf_stanford+regex_v2+guard,"
                                "hf_obi,hf_obi+regex_v2+guard,llm,llm+regex_v2+guard,ai_mask,ai_mask+regex_v2+guard")
dbutils.widgets.text("n_notes", "400")

# COMMAND ----------

import os
import subprocess

ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
endpoint = dbutils.widgets.get("llm_endpoint")
if endpoint:
    os.environ["DEID_LLM_BASE_URL"] = f"https://{ctx.browserHostName().get()}/serving-endpoints"
    os.environ["DEID_LLM_MODEL"] = endpoint
    os.environ["DEID_LLM_API_KEY"] = ctx.apiToken().get()
if dbutils.widgets.get("sql_warehouse_id"):
    os.environ["DATABRICKS_HOST"] = ctx.browserHostName().get()
    os.environ["DATABRICKS_TOKEN"] = ctx.apiToken().get()
    os.environ["DATABRICKS_WAREHOUSE_ID"] = dbutils.widgets.get("sql_warehouse_id")
os.environ["DENTAL_DATA_ROOT"] = "/tmp/dental_data"      # fake-PHI challenge notes stay on the cluster
r = subprocess.run(["python", "../../python/scripts/26_deid_benchmark.py", "--engines", dbutils.widgets.get("engines"),
                    "--n-notes", dbutils.widgets.get("n_notes")], capture_output=True, text=True)
print(r.stdout[-6000:], r.stderr[-2000:])

# COMMAND ----------

import pandas as pd

display(pd.read_csv("/tmp/dental_data/deid/scores.csv"))
display(pd.read_csv("/tmp/dental_data/deid/cost_effectiveness.csv"))
display(pd.read_csv("/tmp/dental_data/deid/not_run.csv"))
