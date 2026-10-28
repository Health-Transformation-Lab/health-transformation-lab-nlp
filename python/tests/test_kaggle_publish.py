"""Publishing the synthetic data and results as Kaggle datasets (spec 018, kaggle/publish.py)."""

import importlib.util
import json
import subprocess
import sys

import pytest

from dental_omop_nlp.paths import REPO_ROOT

_spec = importlib.util.spec_from_file_location("publish", REPO_ROOT / "kaggle" / "publish.py")
pub = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pub)


def _build(tmp_path, name):
    out = tmp_path / name
    subprocess.run([sys.executable, str(REPO_ROOT / "kaggle" / "publish.py"), "--dataset", name, "--out", str(out),
                    "--username", "someone", "--commit", "abc1234"], check=True)
    return out, json.loads((out / "dataset-metadata.json").read_text())


@pytest.mark.parametrize("name", sorted(pub.DATASETS))
def test_listed_files_exist_and_are_neither_simulated_nor_external(name):
    files = pub.files_of(name)
    assert files
    for dest, src in files.items():
        assert src.exists(), src
        rel = src.relative_to(REPO_ROOT).as_posix()
        assert not src.name.startswith("simulated_"), rel
        assert not rel.startswith(("data/external/", "data/raw/")), rel
        assert not dest.startswith("/") and ".." not in dest


@pytest.mark.parametrize("name", sorted(pub.DATASETS))
def test_built_folder_holds_exactly_the_listed_files(tmp_path, name):
    out, _ = _build(tmp_path, name)
    built = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}
    assert built == set(pub.files_of(name)) | {"dataset-metadata.json"}


@pytest.mark.parametrize("name", sorted(pub.DATASETS))
def test_metadata_is_cc_by_with_a_card_and_kaggle_length_limits(tmp_path, name):
    _, meta = _build(tmp_path, name)
    assert meta["licenses"] == [{"name": "CC-BY-4.0"}]
    owner, slug = meta["id"].split("/")
    assert owner == "someone" and 6 <= len(slug) <= 50 and slug == slug.lower()
    assert 6 <= len(meta["title"]) <= 50 and 20 <= len(meta["subtitle"]) <= 80
    card = meta["description"].lower()
    for words in ("synthetic", "not affiliated", "not for clinical", "cc by 4.0", "github.com/jcbowyer/dental-omop-nlp",
                  "abc1234"):
        assert words in card, words
    for f in pub.files_of(name):              # the card lists every file
        assert f"`{f}`" in meta["description"], f


def test_no_simulated_file_reaches_the_results_dataset():
    names = [d.split("/")[-1] for d in pub.files_of("results")]
    assert not [n for n in names if n.startswith("simulated_")]
    assert "ai_predictions_medgemma-1.5-4b-it.csv" in names


def test_workflow_creates_public_then_versions_and_names_the_commit():
    text = (REPO_ROOT / ".github" / "workflows" / "kaggle-publish.yml").read_text()
    assert "kaggle datasets create" in text and "--public" in text
    assert "kaggle datasets version" in text and "kaggle datasets status" in text
    assert "kaggle/publish.py" in text and "github.sha" in text
    assert "environment: dev" in text
