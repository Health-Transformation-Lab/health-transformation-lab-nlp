"""Data locations. Local by default; on Databricks set DENTAL_DATA_ROOT to a
Volume path (e.g. /Volumes/main/dental/data) and everything follows."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(os.environ.get("DENTAL_DATA_ROOT", REPO_ROOT / "data"))

SYNTHEA_CSV = Path(os.environ.get("DENTAL_SYNTHEA_CSV", REPO_ROOT / "synthea" / "output" / "csv"))
OMOP_DIR = DATA_ROOT / "omop"          # one parquet per CDM table
LABELS_DIR = DATA_ROOT / "labels"      # labeled notes + split
RESULTS_DIR = DATA_ROOT / "results"    # scorer output, one file per run
SAMPLES_DIR = REPO_ROOT / "data" / "samples"
MODELS_YAML = REPO_ROOT / "models.yaml"
