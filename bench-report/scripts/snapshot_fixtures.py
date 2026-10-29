"""Snapshot the gold tables every report reads into tests/fixtures/<schema>/, from a Databricks SQL warehouse.
The tests and BENCH_REPORT_SOURCE=fixtures run on this snapshot. Synthetic data only: the gold tables hold the
study's synthetic visits (statuses, never note text).

    DATABRICKS_HOST=... DATABRICKS_WAREHOUSE_ID=... python scripts/snapshot_fixtures.py
    python scripts/snapshot_fixtures.py --web     # only rebuild the front end's payloads from the committed snapshot

Rerunning overwrites every file (idempotent). Each schema folder gets one CSV per table and _types.json with each
column's Databricks type, so DuckDB loads the same types back. Then every report's payload on the snapshot goes to
web/src/__fixtures__/<bench>.<report>.json, for the front end's tests (tests/test_web_fixtures.py checks it's current).
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bench_report import benches, settings, sources  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / "fixtures"
WEB = ROOT / "web" / "src" / "__fixtures__"


def web_payload(bench, report, source, catalog: str) -> dict:
    """What the API returns for a report, less the moment it was generated."""
    return {"bench": bench.key, "bench_name": bench.name, "report": report.key, "title": report.title,
            "summary": report.summary, "gold_schema": f"{catalog}.{bench.gold_schema}", "source": "fixtures",
            "generated_ts": "2026-10-29T00:00:00+00:00", "cached": False,
            **report.run(source, f"{catalog}.{bench.gold_schema}")}


def write_web_fixtures(catalog: str) -> None:
    src = sources.FixtureSource(settings.load({"BENCH_REPORT_SOURCE": "fixtures", "BENCH_REPORT_CATALOG": catalog}))
    WEB.mkdir(parents=True, exist_ok=True)
    for bench in benches.BENCHES:
        for report in bench.reports:
            (WEB / f"{bench.key}.{report.key}.json").write_text(
                json.dumps(web_payload(bench, report, src, catalog), indent=1) + "\n")


def main() -> None:
    if "--web" in sys.argv[1:]:
        write_web_fixtures("health_transformation_lab")
        return
    s = settings.load()
    if s.source != "databricks":
        raise SystemExit("snapshot reads from Databricks: unset BENCH_REPORT_SOURCE")
    src = sources.DatabricksSource(s)
    src.check()
    for bench in benches.BENCHES:
        tables = sorted({t for r in bench.reports for t in r.tables})
        if not tables:
            continue
        folder = OUT / bench.gold_schema
        folder.mkdir(parents=True, exist_ok=True)
        types = {}
        for t in tables:
            full = f"{s.catalog}.{bench.gold_schema}.{t}"
            cols = src.client.tables.get(full).columns
            types[t] = {c.name: c.type_name.value for c in sorted(cols, key=lambda c: c.position)}
            rows = src.query(f"select * from {full} order by all")
            with open(folder / f"{t}.csv", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(types[t]), lineterminator="\n")
                w.writeheader()
                w.writerows(rows)
            print(f"{full}: {len(rows)} rows")
        (folder / "_types.json").write_text(json.dumps(types, indent=2) + "\n")
    write_web_fixtures(s.catalog)


if __name__ == "__main__":
    main()
