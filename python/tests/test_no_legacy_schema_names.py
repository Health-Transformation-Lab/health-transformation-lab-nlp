"""Spec 022 US1: the old schema suffix (dental_omop_perio) survives only in the legacy bundle entries and in
history."""
import subprocess

from health_transformation_lab_nlp.paths import REPO_ROOT

OLD = "dental_omop_perio"
ALLOWED = (
    "pull_requests/", "specs/0", ".specify/", "data/",    # history keeps the names it was written with
    "databricks.yml",                                     # legacy_domain: dev keeps its old schemas
    "docs/deployment.md",                                 # what was renamed, and retiring the legacy schemas
    "python/tests/test_bundle.py", "python/tests/test_no_legacy_schema_names.py",
)


def test_old_schema_name_only_where_allowed():
    files = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-files"], capture_output=True, text=True,
                           check=True).stdout.split()
    found = [f for f in files if not f.startswith(ALLOWED) and not f.endswith(".png")
             and (REPO_ROOT / f).is_file() and OLD in (REPO_ROOT / f).read_text(errors="ignore")]
    assert found == [], f"{OLD} still used in {found}; use the bench schemas (spec 022)"
