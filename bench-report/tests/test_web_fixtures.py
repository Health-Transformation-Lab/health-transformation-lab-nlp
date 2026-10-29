"""The front end's tests draw the payload the API gives on the snapshot; it must be current."""

import json
import sys
from pathlib import Path

from bench_report import benches

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import snapshot_fixtures  # noqa: E402


def test_every_report_has_a_current_web_fixture(fixture_source):
    for bench in benches.BENCHES:
        for report in bench.reports:
            committed = json.loads((snapshot_fixtures.WEB / f"{bench.key}.{report.key}.json").read_text())
            built = json.loads(json.dumps(snapshot_fixtures.web_payload(bench, report, fixture_source,
                                                                        "health_transformation_lab")))
            assert committed == built, "run python scripts/snapshot_fixtures.py --web"
