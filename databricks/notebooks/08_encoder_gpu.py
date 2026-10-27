# Databricks notebook source
# MAGIC %md
# MAGIC # Encoders that need a GPU (spec 002 T017)
# MAGIC
# MAGIC Fine-tunes each encoder in `rungs` on the training notes and predicts the 240 review charts with
# MAGIC `python/scripts/11_ai_predict.py`, the same script that runs the smaller encoders on a laptop.
# MAGIC Synthetic data only. The large ModernBERTs and the Longformers are too slow on CPU; GatorTron-base
# MAGIC diverged on CPU at the default learning rate (every chart called healthy), so `lr_overrides` reruns it
# MAGIC lower.
# MAGIC
# MAGIC Predictions are copied to the landing volume (`encoder_gpu/`) and appended to the table
# MAGIC `encoder_gpu_predictions` in the gold schema. To score them with the other models, copy the CSVs into
# MAGIC `data/datasets/`, then run `python/scripts/28_ladder_vs_truth.py` and `35_readme_results.py`.

# MAGIC
# MAGIC **Packages** come from the job's environment (`databricks/resources/jobs.yml`): a `%pip install`
# MAGIC followed by a Python restart kills the notebook on serverless GPU. Running it by hand, add the
# MAGIC same packages in the notebook's Environment side panel first.

# COMMAND ----------

import os
import shutil
import subprocess
import sys
import tempfile

# The repo's code, for this notebook and the scripts it runs, without installing it.
_REPO_PY = os.path.abspath("../../python")
sys.path.insert(0, _REPO_PY)
os.environ["PYTHONPATH"] = os.pathsep.join(p for p in (_REPO_PY, os.environ.get("PYTHONPATH")) if p)

import pandas as pd
from dental_omop_nlp.paths import DATASETS_DIR, REPO_ROOT
from dental_omop_nlp.rungs import output_tag

dbutils.widgets.text("rungs", "modernbert-large,bioclinical-modernbert-large,longformer-base,clinical-longformer,gatortron-base")  # noqa: F821
dbutils.widgets.text("lr_overrides", "gatortron-base=2e-5")             # noqa: F821  rung=rate, comma-separated
dbutils.widgets.text("epochs", "3")                                     # noqa: F821
dbutils.widgets.text("max_len", "256")                                  # noqa: F821
dbutils.widgets.text("catalog", "dental_omop")                          # noqa: F821  set by databricks.yml
dbutils.widgets.text("schema", "gold_dental_omop_perio")                # noqa: F821
dbutils.widgets.text("landing_schema", "landing_dental_omop_perio")     # noqa: F821
w = {k: dbutils.widgets.get(k) for k in ("rungs", "lr_overrides", "epochs", "max_len", "catalog",  # noqa: F821
                                          "schema", "landing_schema")}

rungs = [r.strip() for r in w["rungs"].split(",") if r.strip()]
lrs = dict(x.strip().split("=") for x in w["lr_overrides"].split(",") if "=" in x)
out_dir = f"/Volumes/{w['catalog']}/{w['landing_schema']}/data/encoder_gpu"
work = tempfile.mkdtemp(prefix="encoder_gpu_")   # training checkpoints: local scratch, not workspace files
os.makedirs(out_dir, exist_ok=True)

# COMMAND ----------

done, failed = [], []
for rung in rungs:
    lr = float(lrs.get(rung, 5e-5))
    cmd = [sys.executable, str(REPO_ROOT / "python" / "scripts" / "11_ai_predict.py"), "--rung", rung,
           "--epochs", w["epochs"], "--max-len", w["max_len"], "--lr", str(lr)]
    print(" ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=work, capture_output=True, text=True, check=False)  # a failure skips one rung
    print(r.stdout[-2000:], r.stderr[-2000:])
    if r.returncode:
        failed.append(rung)
        continue
    method = rung + output_tag(lr=lr)
    path = DATASETS_DIR / f"ai_predictions_{method}.csv"
    shutil.copy(path, out_dir)
    done.append((method, path))

# COMMAND ----------

if done:
    preds = pd.concat([pd.read_csv(p).assign(method=m) for m, p in done])
    spark.createDataFrame(preds).write.mode("append").saveAsTable(  # noqa: F821
        f"{w['catalog']}.{w['schema']}.encoder_gpu_predictions")
print("done:", [m for m, _ in done], "| failed:", failed)
if failed:
    raise RuntimeError(f"encoders that failed: {failed} (the others' predictions are saved)")
