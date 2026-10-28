"""Build the folder `kaggle datasets create/version` uploads: the files, and dataset-metadata.json with the
card (spec 018). Used by .github/workflows/kaggle-publish.yml; public, CC BY 4.0.

    python kaggle/publish.py --dataset notes|results --out build/notes --username <kaggle user> --commit <sha>

Files are listed here, folder by folder, never globbed from the whole tree: nothing from data/external/
(others' datasets) or data/raw/, and no simulated_* file (dry runs would read as results).
"""

import argparse
import csv
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = REPO / "data" / "datasets"
DATASETS = {
    "notes": {"slug": "synthetic-dental-perio-notes", "title": "Synthetic Dental Periodontal Notes and Charts",
              "subtitle": "Synthetic dental chart notes labelled with 2017 AAP/EFP periodontal status",
              "keywords": ["health", "nlp", "text classification", "medicine"],
              "files": [("train.csv", "train.csv"), ("visits_structured.csv", "visits_structured.csv"),
                        ("answer_key/review_key.csv", "review_key.csv"),
                        ("answer_key/visits_truth.csv", "visits_truth.csv"),
                        ("answer_key/clinic_profiles.csv", "clinic_profiles.csv"),
                        ("review_tasks.json", "review_tasks.json")]},
    "results": {"slug": "dental-perio-benchmark-results", "title": "Dental Perio Note Classifier Benchmark",
                "subtitle": "What rules, encoders and LLMs answered on 240 synthetic dental review notes",
                "keywords": ["health", "nlp", "text classification", "model comparison"],
                "globs": [("", "ai_predictions_*.csv"), ("", "llm_details_*.csv"), ("ladder", "*.csv"),
                          ("judge", "*.csv")]},
}


def files_of(name: str) -> dict:
    """{path in the dataset: source file}, in a stable order."""
    d = DATASETS[name]
    out = {dest: DATA / src for src, dest in d.get("files", [])}
    for folder, pattern in d.get("globs", []):
        for src in sorted((DATA / folder).glob(pattern)):
            if not src.name.startswith("simulated_"):
                out[f"{folder}/{src.name}" if folder else src.name] = src
    return out


def _rows(src: Path) -> str:
    if src.suffix == ".json":
        return f"{len(json.loads(src.read_text()))} items"
    with open(src, newline="") as f:
        return f"{sum(1 for _ in csv.reader(f)) - 1:,} rows"


def card(name: str, commit: str) -> str:
    table = "\n".join(f"| `{dest}` | {_rows(src)} |" for dest, src in files_of(name).items())
    return ((HERE / "cards" / f"{name}.md").read_text().rstrip() + "\n\n## Contents\n\n| File | Size |\n|---|---|\n"
            + table + f"\n\nPublished from commit `{commit}` of the repository.\n")


def build(name: str, out: Path, username: str, commit: str) -> dict:
    d = DATASETS[name]
    if out.exists():
        shutil.rmtree(out)
    for dest, src in files_of(name).items():
        (out / dest).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, out / dest)
    meta = {"title": d["title"], "subtitle": d["subtitle"], "id": f"{username}/{d['slug']}",
            "licenses": [{"name": "CC-BY-4.0"}], "keywords": d["keywords"], "description": card(name, commit)}
    (out / "dataset-metadata.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=sorted(DATASETS))
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--username", required=True)
    ap.add_argument("--commit", required=True)
    a = ap.parse_args()
    meta = build(a.dataset, a.out, a.username, a.commit)
    print(f"prepared {meta['id']}: {len(files_of(a.dataset))} files at {a.commit[:12]}")


if __name__ == "__main__":
    main()
