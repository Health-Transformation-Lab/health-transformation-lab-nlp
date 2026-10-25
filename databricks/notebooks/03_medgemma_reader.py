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
# MAGIC **Before running:** accept the HAI-DEF terms for the model on Hugging Face and put a
# MAGIC read token in a secret scope (`dental` / `hf_token`).

# COMMAND ----------

# MAGIC %pip install -q -e ../../python[llm]
# MAGIC %restart_python

# COMMAND ----------

import os
import subprocess

dbutils.widgets.text("rung", "medgemma-1.5-4b-it")  # noqa: F821
dbutils.widgets.text("limit", "40")                  # noqa: F821  start small: GPU quota
dbutils.widgets.text("shots", "0")                   # noqa: F821
os.environ["HF_TOKEN"] = dbutils.secrets.get("dental", "hf_token")  # noqa: F821

import torch  # noqa: E402

print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none (check compute selector)")

# COMMAND ----------

# Build the synthetic datasets if this is a fresh Git folder
if not os.path.exists("../../data/datasets/answer_key/review_key.csv"):
    subprocess.run(["python", "../../python/scripts/10_build_study.py"], check=True)

r = subprocess.run(["python", "../../python/scripts/11_ai_predict.py",
                    "--rung", dbutils.widgets.get("rung"), "--backend", "hf",  # noqa: F821
                    "--limit", dbutils.widgets.get("limit"), "--shots", dbutils.widgets.get("shots")],  # noqa: F821
                   capture_output=True, text=True)
print(r.stdout[-3000:], r.stderr[-3000:])

# COMMAND ----------

import pandas as pd  # noqa: E402

rung = dbutils.widgets.get("rung")  # noqa: F821
d = pd.read_csv(f"../../data/datasets/llm_details_{rung}.csv")
key = pd.read_csv("../../data/datasets/answer_key/review_key.csv").set_index("visit_id")
d["truth"] = key.loc[d.visit_id, "truth_status"].values
d["difficulty"] = key.loc[d.visit_id, "difficulty"].values
print(f"gate pass {d.gate_ok.mean():.1%}, fallback {d.fallback.mean():.1%}, "
      f"{d.latency_s.mean():.1f}s/note -> {1 / d.latency_s.mean():.2f} notes/s unbatched")
display(d.assign(correct=d.pred == d.truth).groupby("difficulty")["correct"].agg(["mean", "size"]))  # noqa: F821
# Against the generator truth only. The study result is against reviewers: 13_reliability.py.

# COMMAND ----------

# Keep the run: Delta table for tracking across runs (prompt variant, shots, adapter)
spark.createDataFrame(d.assign(run_ts=pd.Timestamp.now(tz="UTC"))).write.mode("append").saveAsTable(  # noqa: F821
    "workspace.dental.llm_reader_runs")
