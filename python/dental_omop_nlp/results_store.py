"""Model results as table rows, wherever they ran (spec 016).

    result_files    every non-simulated ai_predictions_<method>.csv and llm_details_<method>.csv in a
                    folder, with its SHA-256 (the file version), row count and source
    new_files       the versions a table hasn't loaded yet
    prediction_rows method, visit_id, pred and provenance (probabilities stay in the CSV)
    detail_rows     every llm_details column and provenance
    record          copy a collected run into the folder and note its source in the manifest
    llm_run_metrics what one loaded LLM run is logged to MLflow with

The manifest (results_manifest.csv, committed next to the files) says where a file came from: kaggle
plus the workflow run URL for a collected Kaggle run. A file it doesn't list is `repo`: made locally
and committed. simulated_* files are never results.
"""

from __future__ import annotations

import hashlib
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .telemetry import traced

MANIFEST = "results_manifest.csv"
MANIFEST_COLUMNS = ["file", "source", "run_url", "recorded_at"]
PATTERN = re.compile(r"^(ai_predictions|llm_details)_(.+)\.csv$")
KINDS = {"ai_predictions": "predictions", "llm_details": "llm_details"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@traced
def read_manifest(folder: Path) -> pd.DataFrame:
    path = Path(folder) / MANIFEST
    if not path.exists():
        return pd.DataFrame(columns=MANIFEST_COLUMNS)
    return pd.read_csv(path, dtype=str).fillna("")


@traced
def result_files(folder: Path) -> pd.DataFrame:
    folder = Path(folder)
    manifest = read_manifest(folder).set_index("file")
    rows = []
    for path in sorted(folder.glob("*.csv")):
        m = PATTERN.match(path.name)
        if not m:
            continue                                    # simulated_*, the manifest and everything else
        src = manifest.loc[path.name] if path.name in manifest.index else None
        rows.append({"file": path.name, "kind": KINDS[m.group(1)], "method": m.group(2), "sha256": _sha256(path),
                     "rows": len(pd.read_csv(path, usecols=["visit_id"])),
                     "source": src["source"] if src is not None else "repo",
                     "run_url": src["run_url"] if src is not None else ""})
    return pd.DataFrame(rows, columns=["file", "kind", "method", "sha256", "rows", "source", "run_url"])


@traced
def new_files(files: pd.DataFrame, loaded_sha256: set) -> pd.DataFrame:
    return files[~files.sha256.isin(loaded_sha256)].reset_index(drop=True)


def _with_provenance(files: pd.DataFrame, folder: Path, columns: list | None) -> pd.DataFrame:
    parts = [pd.read_csv(Path(folder) / f.file).assign(method=f.method, sha256=f.sha256, source=f.source)
             for f in files.itertuples()]
    if not parts:
        return pd.DataFrame(columns=columns or [])
    out = pd.concat(parts, ignore_index=True)
    return out[columns] if columns else out


@traced
def prediction_rows(files: pd.DataFrame, folder: Path) -> pd.DataFrame:
    return _with_provenance(files, folder, ["method", "visit_id", "pred", "sha256", "source"])


@traced
def detail_rows(files: pd.DataFrame, folder: Path) -> pd.DataFrame:
    return _with_provenance(files, folder, None)


@traced
def record(src: Path, dest: Path, run_url: str, source: str = "kaggle", min_rows: int = 0) -> list[str]:
    """Copy src's result files into dest and list them in dest's manifest. Raises ValueError, changing
    nothing, if there are none, or one has fewer rows than min_rows (a full run) or than the file it would
    replace: a test run is never committed, even under a new name (shots or adapter tags the method)."""
    src, dest = Path(src), Path(dest)
    found = result_files(src)
    if found.empty:
        raise ValueError(f"no result files (ai_predictions_*.csv, llm_details_*.csv) in {src}")
    for f in found.itertuples():
        old = dest / f.file
        n = max(min_rows, len(pd.read_csv(old, usecols=["visit_id"])) if old.exists() else 0)
        if f.rows < n:
            raise ValueError(f"{f.file} has fewer rows ({f.rows}) than a full run ({n}): "
                             "a test run is not committed")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = read_manifest(dest)
    manifest = manifest[~manifest.file.isin(found.file)]
    for f in found.itertuples():
        shutil.copy(src / f.file, dest / f.file)
    added = pd.DataFrame({"file": found.file, "source": source, "run_url": run_url, "recorded_at": now})
    pd.concat([manifest, added], ignore_index=True).sort_values("file").to_csv(dest / MANIFEST, index=False)
    return list(found.file)


@traced
def llm_run_metrics(details: pd.DataFrame, truth: pd.Series) -> dict:
    """truth: answer-key status indexed by visit_id."""
    agree = details.pred.eq(details.visit_id.map(truth))
    return {"rows": len(details),
            "gate_fail_rate": float((~details.gate_ok.astype(bool)).mean()),
            "fallback_rate": float(details.fallback.astype(bool).mean()),
            "agreement_with_key": float(agree.mean())}
