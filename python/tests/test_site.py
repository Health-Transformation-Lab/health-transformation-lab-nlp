"""The lab's website (issue #168): website/ is published by GitHub Pages at healthtransformationlab.org. It carries the
same labels as the landing README, puts PerioBench first, and every link into the repo names a file that exists."""

import re

from health_transformation_lab_nlp.paths import REPO_ROOT

SITE = REPO_ROOT / "website"
REPO_URL = "https://github.com/Health-Transformation-Lab/health-transformation-lab-nlp"


def _page():
    return (SITE / "index.html").read_text(encoding="utf-8")


def _text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<(style|script)[^>]*>.*?</\1>", "", html, flags=re.S)))


def test_the_site_answers_at_the_lab_domain():
    assert (SITE / "CNAME").read_text() == "healthtransformationlab.org\n"


def test_the_page_says_personal_project_synthetic_and_not_affiliated():
    text = _text(_page())
    assert "Personal learning project" in text and "not affiliated" in text
    assert "synthetic" in text.lower() and "not clinical performance" in text


def test_periobench_comes_first_and_its_goal_is_patient_care():
    text = _text(_page())
    order = [text.index(f"{name}:") for name in ("PerioBench", "OralHealthBench", "AccessBench")]
    assert order == sorted(order)
    assert "better care" in text[order[0]:order[1]]


def test_every_link_is_external_or_an_anchor_and_repo_links_name_real_files():
    html = _page()
    anchors = set(re.findall(r'id="([^"]+)"', html))
    for href in re.findall(r'href="([^"]+)"', html):
        if href.startswith("#"):
            assert href[1:] in anchors, href
            continue
        assert href.startswith("https://"), href
        if href.startswith(f"{REPO_URL}/blob/main/"):
            path = href.removeprefix(f"{REPO_URL}/blob/main/").split("#")[0]
            assert (REPO_ROOT / path).exists(), href


def test_pages_publishes_the_site_folder_on_merge():
    import yaml
    wf = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "pages.yml").read_text())
    push = wf[True]["push"]                                     # yaml reads the `on:` key as True
    assert push["branches"] == ["main"] and "website/**" in push["paths"]
    steps = [s for job in wf["jobs"].values() for s in job["steps"]]
    upload = next(s for s in steps if "upload-pages-artifact" in s.get("uses", ""))
    assert upload["with"]["path"] == "website"
    assert any("deploy-pages" in s.get("uses", "") for s in steps)
