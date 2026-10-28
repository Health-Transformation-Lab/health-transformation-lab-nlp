"""The slide decks (docs/<deck>/slides/, built by docs/build_decks.py) and the landing page that links them
(issue #100): the built files match their slides, every figure slide names its source, and the landing README
offers the two paths."""

import importlib.util
import re

import pytest

from dental_omop_nlp.paths import REPO_ROOT

_spec = importlib.util.spec_from_file_location("build_decks", REPO_ROOT / "docs" / "build_decks.py")
build_decks = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_decks)


@pytest.mark.parametrize("deck", sorted(build_decks.DECKS))
def test_built_deck_and_full_text_match_the_slides(deck):
    html, md = build_decks.render(deck)
    folder = REPO_ROOT / "docs" / deck
    stale = f"run python docs/build_decks.py ({deck})"
    assert (folder / "deck.html").read_text(encoding="utf-8") == html, stale
    assert (folder / "full_text_and_notes.md").read_text(encoding="utf-8") == md, stale


@pytest.mark.parametrize("deck", sorted(build_decks.DECKS))
def test_every_slide_has_speaker_notes(deck):
    for sid, _, notes in build_decks.slides(REPO_ROOT / "docs" / deck):
        assert notes, f"{deck}/{sid} has no <aside> notes"


def test_edr_deck_labels_its_numbers_synthetic_or_cites_them():
    # a dry run is never a result: every EDR slide with a figure says synthetic, illustrative, or names a source
    for sid, section, _ in build_decks.slides(REPO_ROOT / "docs" / "edr"):
        text = " ".join(build_decks.visible_text(section))
        if re.search(r"\d+ of \d+|\d+%|\$\d", text):
            assert re.search(r"[Ss]ynthetic|[Ii]llustrative|\b(19|20)\d\d\b", text), sid


def test_landing_readme_offers_two_paths_each_with_an_executive_and_a_detailed_route():
    readme = (REPO_ROOT / "README.md").read_text()
    assert "Personal learning project" in readme and "DISCLAIMER.md" in readme
    for link in ("docs/edr/deck.html", "docs/edr/README.md", "docs/pitch/deck.html", "docs/pitch/README.md"):
        assert f"]({link}" in readme, link
    assert len(readme.splitlines()) <= 80                     # a landing page, not the study
