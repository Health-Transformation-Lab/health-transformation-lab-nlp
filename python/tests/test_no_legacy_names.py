"""Spec 021 US1: the old schema suffix (dental_omop_perio) survives only where the move needs it or history
records it."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = "dental_omop_perio"
ALLOWED = (
    "pull_requests/",                                     # reviews keep the names they were written with
    "specs/012-", "specs/016-", "specs/018-", "specs/019-", "specs/021-",   # history, and this spec
    "databricks.yml",                                     # legacy_domain: the old schemas stay declared
    "databricks/notebooks/12_migrate_bench_schemas.py",   # the migration
    "python/dental_omop_nlp/schemas.py",                  # the old -> new map
    "docs/deployment.md",                                 # what moved, and retiring the legacy schemas
    "python/tests/test_schemas.py", "python/tests/test_bundle.py", "python/tests/test_no_legacy_names.py",
)


def test_old_schema_name_only_where_allowed():
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    found = [f for f in files if not f.startswith(ALLOWED)
             and (ROOT / f).is_file() and OLD in (ROOT / f).read_text(errors="ignore")]
    assert found == [], f"{OLD} still used in {found}; use the perio_bench schemas (spec 021)"
