"""Which tables the Genie spaces read don't exist yet? (issue #155)

A Genie space can't be created before the tables it reads (Databricks answers 403), and the Load results job that
writes the grader tables runs after the deploy. So the spaces are their own bundle (databricks/genie/), and the deploy
workflow creates them only when this prints nothing.

    python .github/scripts/genie_tables_missing.py    # prints the missing tables, comma-separated; empty if none
"""

import json
import subprocess
import sys
from pathlib import Path

GENIE_DIR = Path(__file__).resolve().parents[2] / "databricks" / "genie"


def space_tables(folder: Path = GENIE_DIR) -> list[str]:
    """Every table identifier any space in the folder reads."""
    out = set()
    for f in sorted(Path(folder).glob("*.geniespace.json")):
        out |= {t["identifier"] for t in json.loads(f.read_text())["data_sources"]["tables"]}
    return sorted(out)


def _exists(table: str) -> bool:
    return subprocess.run(["databricks", "tables", "get", table], capture_output=True, check=False).returncode == 0


def missing(tables: list[str], exists=_exists) -> list[str]:
    return [t for t in tables if not exists(t)]


if __name__ == "__main__":
    gone = missing(space_tables())
    print(", ".join(gone))
    print(f"{len(gone)} of the Genie spaces' tables missing", file=sys.stderr)
