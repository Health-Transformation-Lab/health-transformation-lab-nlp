"""Issue #374: the built decks reach the website (healthtransformationlab.github.io) on their own when they change
on main. .github/scripts/site_decks.py builds the site's copies; .github/workflows/site-decks.yml pushes them."""

import importlib.util

import pytest
import yaml

from health_transformation_lab_nlp.paths import REPO_ROOT

_spec = importlib.util.spec_from_file_location("site_decks", REPO_ROOT / ".github" / "scripts" / "site_decks.py")
sd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sd)


def test_each_deck_goes_to_its_page_with_the_sites_icon_links(tmp_path):
    changed = sd.copy(REPO_ROOT, tmp_path)
    assert set(changed) == {"perio-bench/index.html", "oral-health-bench/index.html", "img/edr_deck_cover.png",
                            "img/pitch_deck_cover.png"}
    for deck, page in (("edr", "perio-bench"), ("pitch", "oral-health-bench")):
        src = (REPO_ROOT / "docs" / deck / "deck.html").read_text(encoding="utf-8")
        out = (tmp_path / page / "index.html").read_text(encoding="utf-8")
        assert out == src.replace("</title>", "</title>" + sd.ICONS, 1)
    for img in ("edr_deck_cover.png", "pitch_deck_cover.png"):
        assert (tmp_path / "img" / img).read_bytes() == (REPO_ROOT / "docs" / "img" / img).read_bytes()


def test_a_second_copy_changes_nothing(tmp_path):
    sd.copy(REPO_ROOT, tmp_path)
    assert sd.copy(REPO_ROOT, tmp_path) == []                    # idempotent: no empty commits on the site


def test_a_deck_without_a_title_is_refused(tmp_path):
    (tmp_path / "src" / "docs" / "edr").mkdir(parents=True)
    (tmp_path / "src" / "docs" / "edr" / "deck.html").write_text("<html>no title</html>")
    with pytest.raises(SystemExit, match="title"):
        sd.copy(tmp_path / "src", tmp_path / "site")


def test_the_token_check_fails_fast_and_names_the_setting():
    with pytest.raises(SystemExit, match="SITE_DEPLOY_TOKEN is not set"):
        sd.check_token("", repo_info=lambda t: {})
    with pytest.raises(SystemExit, match="doesn't look like a GitHub token"):
        sd.check_token("hf_abc", repo_info=lambda t: {})
    with pytest.raises(SystemExit, match="can't push"):
        sd.check_token("github_pat_x", repo_info=lambda t: {"permissions": {"push": False}})
    assert sd.check_token("github_pat_x", repo_info=lambda t: {"permissions": {"push": True}}) is None


def test_the_workflow_runs_when_a_deck_changes_and_checks_the_token_first():
    wf = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "site-decks.yml").read_text())
    on = wf[True]
    assert on["push"]["branches"] == ["main"] and "workflow_dispatch" in on
    for path in ("docs/edr/deck.html", "docs/pitch/deck.html", "docs/img/*_deck_cover.png",
                 ".github/scripts/site_decks.py"):
        assert path in on["push"]["paths"], path
    job = next(iter(wf["jobs"].values()))
    names = [s.get("name", "") for s in job["steps"]]
    check = names.index("Check the site token (value stays masked)")
    push = next(i for i, n in enumerate(names) if n.startswith("Copy the decks"))
    assert check < push
    assert "SITE_DEPLOY_TOKEN" in str(job["steps"][check]["env"])


def test_the_site_token_is_in_the_register():
    reg = yaml.safe_load((REPO_ROOT / "ops" / "secrets_register.yaml").read_text())["credentials"]
    tok = next(c for c in reg if "SITE_DEPLOY_TOKEN" in c["stored_in"])
    assert "healthtransformationlab.github.io" in tok["scope"] and "Contents" in tok["scope"]
    assert "site-decks.yml" in tok["used_by"]
