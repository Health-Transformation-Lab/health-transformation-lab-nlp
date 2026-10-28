"""The rule in AGENTS.md ("Words"): we find gum disease in records, we don't diagnose. "Diagnosis" may name what a
dentist recorded (a diagnosis code), never what our rules, models or agents do. AGENTS.md, which states the rule, and
this test are the only files allowed the phrases; past PR reviews in pull_requests/ are records and stay as written;
a quote from a cited paper goes in QUOTED."""

import re
import subprocess

from health_transformation_lab_nlp.paths import REPO_ROOT

PHRASES = re.compile(
    r"\b(misdiagnos\w*"
    r"|diagnostic tools?"
    r"|(?:in)?accurate(?:ly)? diagnos\w*"
    r"|diagnos\w* (?:accuracy|is accurate)"
    r"|(?:AI|models?|rules|agents?|LLMs?) (?:can |to |that )?diagnos(?:e|es|ing)\b"
    r"|wrong diagnos\w*)",
    re.IGNORECASE)
ALLOWED = {"AGENTS.md", "python/tests/test_wording.py"}
QUOTED = {"docs/rag_and_vocabulary.md": "MedRAG"}   # file: text on the line that marks it as a cited paper's words


def _tracked_files():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=REPO_ROOT, capture_output=True, check=True).stdout
    return [f for f in out.decode().split("\0") if f]


def test_no_file_says_we_diagnose():
    hits = []
    for rel in _tracked_files():
        path = REPO_ROOT / rel
        if rel in ALLOWED or rel.startswith("pull_requests/") or not path.is_file():
            continue
        data = path.read_bytes()
        if b"\0" in data[:8192]:            # binary: images, archives
            continue
        for n, line in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
            if PHRASES.search(line) and not (rel in QUOTED and QUOTED[rel] in line):
                hits.append(f"{rel}:{n}: {PHRASES.search(line).group(0)}")
    assert not hits, "See AGENTS.md, 'Words': reword these:\n" + "\n".join(hits)


def test_agents_md_states_the_rule():
    assert "## Words" in (REPO_ROOT / "AGENTS.md").read_text()
