"""The rule in CLAUDE.md ("Organization names"): one organization is never referenced in this repo. CLAUDE.md, which
states the rule, is the only file allowed to name it. The name is built from parts so this test doesn't match itself."""

import re
import subprocess

from health_transformation_lab_nlp.paths import REPO_ROOT

NAME = re.compile(r"\b" + "care" + r"[\s_-]?" + "quest" + r"s?\b", re.IGNORECASE)   # not "care questions"
ALLOWED = {"CLAUDE.md"}


def _tracked_files():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=REPO_ROOT, capture_output=True, check=True).stdout
    return [f for f in out.decode().split("\0") if f]


def test_no_file_references_the_organization_named_in_claude_md():
    hits = []
    for rel in _tracked_files():
        path = REPO_ROOT / rel
        if rel in ALLOWED or not path.is_file():
            continue
        if NAME.search(rel):
            hits.append(f"{rel} (file name)")
        data = path.read_bytes()
        if b"\0" in data[:8192]:            # binary: images, archives
            continue
        for n, line in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
            if NAME.search(line):
                hits.append(f"{rel}:{n}")
    assert not hits, "See CLAUDE.md, 'Organization names': remove these references:\n" + "\n".join(hits)


def test_claude_md_states_the_rule():
    assert NAME.search((REPO_ROOT / "CLAUDE.md").read_text())
