# Databricks notebook source
# MAGIC %md
# MAGIC # NHANES 2009-2014 periodontal prevalence (spec 013 G4)
# MAGIC
# MAGIC Downloads the public-domain CDC files (OHXPER, OHXDEN and DEMO for 2009-10, 2011-12, 2013-14) to
# MAGIC the landing volume, classifies every adult 30+ under CDC/AAP 2012 and ACES, and writes the
# MAGIC survey-weighted prevalence with 95% CIs next to the published figures (Eke 2018; Tay 2025).
# MAGIC These are real charts from a public survey; only the aggregate table is meant to come back to the
# MAGIC repo (`data/datasets/nhanes/`). Serverless CPU is enough.

# COMMAND ----------

# MAGIC %pip install -q -e ../../python

# COMMAND ----------

dbutils.library.restartPython()  # noqa: F821

# COMMAND ----------

import subprocess
import sys

from dental_omop_nlp.paths import REPO_ROOT

dbutils.widgets.text("data_dir", "/Volumes/dental_omop/landing_dental_omop_perio/data/nhanes_raw")  # noqa: F821
dbutils.widgets.text("out_dir", "/Volumes/dental_omop/landing_dental_omop_perio/data/nhanes")      # noqa: F821
data_dir, out_dir = dbutils.widgets.get("data_dir"), dbutils.widgets.get("out_dir")              # noqa: F821

cmd = [sys.executable, str(REPO_ROOT / "python" / "scripts" / "38_nhanes_perio.py"),
       "--data-dir", data_dir, "--out", out_dir, "--download"]
r = subprocess.run(cmd, capture_output=True, text=True, check=False)
print(r.stdout[-6000:], r.stderr[-4000:])
if r.returncode:
    raise RuntimeError("NHANES script failed (see output above)")
