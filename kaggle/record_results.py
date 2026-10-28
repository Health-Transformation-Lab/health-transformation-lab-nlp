"""Record a collected Kaggle run in the repo (spec 016): copy its ai_predictions_*.csv and llm_details_*.csv
into data/datasets/ and note source and run URL in results_manifest.csv. Used by kaggle-medgemma.yml.

    python kaggle/record_results.py --from build/output --run-url <workflow run URL> [--to data/datasets]

Exit 3, changing nothing, when there are no result files or one has fewer rows than a full run (every
review note, or the committed file if larger): a 10-note test is never committed. simulated_* files are
never copied.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

import pandas as pd
from health_transformation_lab_nlp.paths import DATASETS_DIR
from health_transformation_lab_nlp.results_store import record


def full_run_rows() -> int:
    """A full run reads every review note in the answer key."""
    return len(pd.read_csv(DATASETS_DIR / "answer_key" / "review_key.csv", usecols=["visit_id"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--from", dest="src", required=True)
    ap.add_argument("--to", default=str(DATASETS_DIR))
    ap.add_argument("--run-url", required=True)
    ap.add_argument("--source", default="kaggle")
    ap.add_argument("--min-rows", type=int, default=None, help="rows a full run has (default: every review note)")
    a = ap.parse_args()
    try:
        min_rows = full_run_rows() if a.min_rows is None else a.min_rows
        files = record(Path(a.src), Path(a.to), a.run_url, a.source, min_rows)
    except ValueError as e:
        print(f"Not recorded: {e}")
        return 3
    print("recorded:", ", ".join(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
