# Databricks notebook source
# MAGIC %md
# MAGIC # MedGemma as a note reader (exploratory, spec 004)
# MAGIC
# MAGIC Personal learning project; synthetic notes only. See `docs/medgemma.md`.
# MAGIC
# MAGIC **Compute:** on Free Edition pick the serverless **GPU** option in the notebook compute
# MAGIC selector (limited, subject to capacity and fair use). Free Edition has no GPU serving
# MAGIC endpoints, so the model runs here in the notebook. On paid workspaces you can instead
# MAGIC serve it and use `--backend openai` or `ai_query`.
# MAGIC
# MAGIC **Compare with BERT:** set `limit` to 0 (all 240 review charts), optionally `lora_train` to
# MAGIC fine-tune first (the BERT encoders were fine-tuned on the same `train.csv`); the last cells run
# MAGIC `29_medgemma_vs_bert.py` against the committed encoder predictions.
# MAGIC
# MAGIC **Before running:** accept the HAI-DEF terms for the model on Hugging Face and put a
# MAGIC read token in a secret scope (`dental` / `hf_token`).

# COMMAND ----------

# MAGIC %pip install -q -e ../../python[llm,lora]
# MAGIC %restart_python

# COMMAND ----------

import os
import subprocess

dbutils.widgets.text("rung", "medgemma-1.5-4b-it")  # noqa: F821
dbutils.widgets.text("limit", "40")                  # noqa: F821  start small: GPU quota
dbutils.widgets.text("shots", "0")                   # noqa: F821
dbutils.widgets.text("lora_train", "0")              # noqa: F821  >0: LoRA fine-tune on this many train notes first
dbutils.widgets.text("catalog", "workspace")         # noqa: F821  set per target by databricks.yml
dbutils.widgets.text("schema", "dental_dev")         # noqa: F821
dbutils.widgets.text("hf_secret_scope", "dental")    # noqa: F821
catalog, schema = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")  # noqa: F821
os.environ["HF_TOKEN"] = dbutils.secrets.get(dbutils.widgets.get("hf_secret_scope"), "hf_token")  # noqa: F821

import torch  # noqa: E402

print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none (check compute selector)")

# COMMAND ----------

# Build the synthetic datasets if this is a fresh Git folder
if not os.path.exists("../../data/datasets/answer_key/review_key.csv"):
    subprocess.run(["python", "../../python/scripts/10_build_study.py"], check=True)

adapter = None
if int(dbutils.widgets.get("lora_train") or 0):  # noqa: F821
    adapter = "/tmp/medgemma-lora"
    r = subprocess.run(["python", "../../python/scripts/17_medgemma_lora.py", "--rung", dbutils.widgets.get("rung"),  # noqa: F821
                        "--max-train", dbutils.widgets.get("lora_train"), "--out", adapter],  # noqa: F821
                       capture_output=True, text=True, check=True)
    print(r.stdout[-2000:], r.stderr[-2000:])

args = ["python", "../../python/scripts/11_ai_predict.py", "--rung", dbutils.widgets.get("rung"),  # noqa: F821
        "--backend", "hf", "--shots", dbutils.widgets.get("shots")]  # noqa: F821
if adapter:
    args += ["--adapter", adapter]
if int(dbutils.widgets.get("limit") or 0):  # noqa: F821  0 = all review notes
    args += ["--limit", dbutils.widgets.get("limit")]  # noqa: F821
r = subprocess.run(args, capture_output=True, text=True)
print(r.stdout[-3000:], r.stderr[-3000:])

# COMMAND ----------

import pandas as pd  # noqa: E402

from dental_omop_nlp.rungs import output_tag  # noqa: E402

rung = dbutils.widgets.get("rung") + output_tag(adapter=adapter, shots=int(dbutils.widgets.get("shots")))  # noqa: F821
d = pd.read_csv(f"../../data/datasets/llm_details_{rung}.csv")
key = pd.read_csv("../../data/datasets/answer_key/review_key.csv").set_index("visit_id")
d["truth"] = key.loc[d.visit_id, "truth_status"].values
d["difficulty"] = key.loc[d.visit_id, "difficulty"].values
print(f"gate pass {d.gate_ok.mean():.1%}, fallback {d.fallback.mean():.1%}, "
      f"{d.latency_s.mean():.1f}s/note -> {1 / d.latency_s.mean():.2f} notes/s unbatched")
display(d.assign(correct=d.pred == d.truth).groupby("difficulty")["correct"].agg(["mean", "size"]))  # noqa: F821
# Against the generator truth only. The study result is against reviewers: 13_reliability.py.

# COMMAND ----------

# MedGemma vs the fine-tuned BERT encoders (committed ai_predictions_<encoder>.csv), paired bootstrap CIs.
# Meaningful only with limit = 0: the encoders scored all 240 charts.
if int(dbutils.widgets.get("limit") or 0):  # noqa: F821
    print("skipped: set limit to 0 so MedGemma scores all 240 charts, as the encoders did")
else:
    r = subprocess.run(["python", "../../python/scripts/29_medgemma_vs_bert.py"], capture_output=True, text=True,
                       check=False)
    print(r.stdout[-4000:], r.stderr[-2000:])
    if r.returncode == 0:
        display(pd.read_csv("../../data/datasets/ladder/medgemma_vs_bert.csv"))  # noqa: F821

# COMMAND ----------

# Keep the run: Delta table for tracking across runs (prompt variant, shots, adapter)
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")  # noqa: F821
spark.createDataFrame(d.assign(run_ts=pd.Timestamp.now(tz="UTC"))).write.mode("append").saveAsTable(  # noqa: F821
    f"{catalog}.{schema}.llm_reader_runs")
