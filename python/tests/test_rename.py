"""Spec 021: the old project names are gone from code, config, tests and current docs. Schema names
are spec 022's (`<layer>_<bench>`, test_no_legacy_schema_names.py)."""

import re
import subprocess

from health_transformation_lab_nlp.paths import REPO_ROOT

OLD = re.compile(r"dental_omop_nlp|dental-omop-nlp|dental_omop\b(?!_)|dental-omop-medgemma|"
                 r"rg-dental-omop|secret scope `dental`|`dental` (?:secret )?scope|\(`dental` /|"
                 r"\| `hf_secret_scope` \| `dental`|scope dental\b|\"dental\"\)")
KEPT = ("dental-omop-ci", "dental-omop-medgemma-keras-test") + tuple(f"dental_omop_nlp_{t}_{k}" for t in ("${bundle.target}", "${target}", "${TARGET}",
        "{target}", "<target>", "dev", "uat", "prod") for k in ("admin", "sp"))   # identities keep their names
HISTORY = ("pull_requests/", "specs/0", ".specify/", "data/")   # past records keep the names they had


def test_no_old_names_left():
    files = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-files"], capture_output=True, text=True,
                           check=True).stdout.split()
    hits = []
    for f in files:
        if f.startswith(HISTORY) and not f.startswith("specs/021"):
            continue
        if f == "python/tests/test_rename.py" or f.endswith((".png", ".gz", ".parquet", ".zip", ".pptx", ".xlsx")):
            continue
        try:
            text = (REPO_ROOT / f).read_text()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        for kept in KEPT:
            text = text.replace(kept, "")
        if f.startswith("specs/021"):
            continue                                     # the spec states the old names on purpose
        for m in OLD.finditer(text):
            hits.append(f"{f}: {m.group(0)}")
    assert not hits, "\n".join(hits[:40])


def test_repo_links_name_the_org():
    """The repo moved to the Health-Transformation-Lab org (#166); GitHub's redirect from the old owner
    lasts only until a repo with the old name is made there, and the Kaggle notebooks clone it."""
    files = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-files"], capture_output=True, text=True,
                           check=True).stdout.split()
    old = re.compile(r"jcbowyer/(?:health-transformation-lab-nlp|dental-omop-nlp)")
    hits = []
    for f in files:
        if f.startswith(HISTORY) or f == "python/tests/test_rename.py" or f.endswith((".png", ".gz", ".parquet", ".zip", ".pptx", ".xlsx")):
            continue
        try:
            text = (REPO_ROOT / f).read_text()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        hits += [f"{f}: {m.group(0)}" for m in old.finditer(text)]
    assert not hits, "\n".join(hits[:40])


def test_telemetry_names_the_lab_as_its_data_product():
    from health_transformation_lab_nlp import telemetry
    assert telemetry.TelemetryConfig().data_product_id == "health_transformation_lab"
