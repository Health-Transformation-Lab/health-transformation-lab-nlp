"""Copy the built decks to the website repository (issue #374), as .github/workflows/site-decks.yml does on every
push to main that changes them.

The site (healthtransformationlab/healthtransformationlab.github.io) serves docs/edr/deck.html as
perio-bench/index.html and docs/pitch/deck.html as oral-health-bench/index.html, each with the site's icon links
added after <title>, and the two deck covers under img/. That is the only difference, so the copies are made here
and never edited on the site.

    python .github/scripts/site_decks.py check                 # SITE_DEPLOY_TOKEN: shape, then one API call
    python .github/scripts/site_decks.py copy <site checkout>  # prints each file it changed
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SITE = "healthtransformationlab/healthtransformationlab.github.io"
ICONS = ('<link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" href="/favicon.svg" type="image/svg+xml">'
         '<link rel="apple-touch-icon" href="/apple-touch-icon.png"><link rel="manifest" href="/site.webmanifest">'
         '<meta name="theme-color" content="#0F2A33">')
DECKS = {"docs/edr/deck.html": "perio-bench/index.html", "docs/pitch/deck.html": "oral-health-bench/index.html"}
IMAGES = {"docs/img/edr_deck_cover.png": "img/edr_deck_cover.png",
          "docs/img/pitch_deck_cover.png": "img/pitch_deck_cover.png"}


def copy(repo: Path, site: Path) -> list:
    """Write the site's copies; return the site paths that changed (none on a second run)."""
    changed = []
    for src, dest in DECKS.items():
        html = (repo / src).read_text(encoding="utf-8")
        if "</title>" not in html:
            raise SystemExit(f"{src} has no </title>, so the site's icon links have nowhere to go")
        new = html.replace("</title>", "</title>" + ICONS, 1).encode("utf-8")
        changed += _write(site / dest, new, dest)
    for src, dest in IMAGES.items():
        changed += _write(site / dest, (repo / src).read_bytes(), dest)
    return changed


def _write(path: Path, data: bytes, name: str) -> list:
    if path.exists() and path.read_bytes() == data:
        return []
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return [name]


def check_token(token: str, repo_info) -> None:
    """Fail fast, naming the setting: missing, wrong shape, or unable to push to the site. Never prints the token."""
    if not token:
        raise SystemExit("SITE_DEPLOY_TOKEN is not set in the GitHub environment 'dev' (docs/operations.md)")
    if not token.startswith(("github_pat_", "ghp_")):
        raise SystemExit("SITE_DEPLOY_TOKEN doesn't look like a GitHub token (github_pat_... or ghp_...)")
    if not (repo_info(token).get("permissions") or {}).get("push"):
        raise SystemExit(f"SITE_DEPLOY_TOKEN can't push to {SITE}: give it Contents read and write on that repository")


def _repo_info(token: str) -> dict:
    req = urllib.request.Request(f"https://api.github.com/repos/{SITE}",
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"SITE_DEPLOY_TOKEN was refused by GitHub ({e.code}): can it read {SITE}?") from None


if __name__ == "__main__":
    if sys.argv[1:2] == ["check"]:
        check_token(os.environ.get("SITE_DEPLOY_TOKEN", "").strip(), _repo_info)
        print(f"SITE_DEPLOY_TOKEN can push to {SITE}")
    elif sys.argv[1:2] == ["copy"] and len(sys.argv) == 3:
        for name in copy(REPO, Path(sys.argv[2])):
            print(name)
    else:
        raise SystemExit(__doc__)
