"""The Kaggle MedGemma notebook stays runnable: valid notebook, flags the script really has, no secrets."""

import json
import re

from dental_omop_nlp.paths import REPO_ROOT

NB = REPO_ROOT / "kaggle" / "medgemma_reader.ipynb"


def _code():
    nb = json.loads(NB.read_text())
    assert nb["nbformat"] == 4
    return "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")


def test_notebook_uses_flags_the_script_has():
    script = (REPO_ROOT / "python" / "scripts" / "11_ai_predict.py").read_text()
    used = set(re.findall(r"11_ai_predict\.py[^\n]*", _code()))
    assert used
    for line in used:
        for flag in re.findall(r"(--[a-z][a-z-]*)", line):
            assert f'"{flag}"' in script, flag


def test_notebook_reads_the_token_from_kaggle_secrets_and_holds_none():
    code = _code()
    assert 'UserSecretsClient().get_secret("HF_TOKEN")' in code
    assert not re.search(r"hf_[A-Za-z0-9]{20,}", NB.read_text())
