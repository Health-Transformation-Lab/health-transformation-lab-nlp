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


# ---- pushing it to Kaggle from GitHub Actions (kaggle/prepare_kernel.py, .github/workflows/kaggle-medgemma.yml)

def _prepare(tmp_path, *extra):
    import subprocess
    import sys
    out = tmp_path / "kernel"
    subprocess.run([sys.executable, str(REPO_ROOT / "kaggle" / "prepare_kernel.py"), "--out", str(out),
                    "--username", "someone", *extra], check=True)
    return out, json.loads((out / "kernel-metadata.json").read_text()), \
        json.loads((out / "medgemma_reader.ipynb").read_text())


def _settings(nb):
    return "".join(next(c["source"] for c in nb["cells"] if "RUNG =" in "".join(c["source"])))


def test_prepared_kernel_runs_on_a_gpu_with_internet_and_the_chosen_settings(tmp_path):
    _, meta, nb = _prepare(tmp_path, "--rung", "medgemma-4b-it", "--limit", "5", "--shots", "2", "--branch", "dev-x")
    assert meta["id"] == "someone/dental-omop-medgemma-reader" and meta["code_file"] == "medgemma_reader.ipynb"
    assert meta["enable_gpu"] is True and meta["enable_internet"] is True and meta["is_private"] is True
    assert meta["kernel_type"] == "notebook" and meta["language"] == "python"
    s = _settings(nb)
    assert 'RUNG = "medgemma-4b-it"' in s and "TEST_NOTES = 5" in s and "SHOTS = 2" in s
    assert 'BRANCH = "dev-x"' in s and "FULL_RUN = False" in s


def test_limit_zero_means_the_full_run(tmp_path):
    _, _, nb = _prepare(tmp_path, "--limit", "0")
    assert "FULL_RUN = True" in _settings(nb)


def test_full_run_cell_only_runs_when_asked():
    code = _code()
    assert "if FULL_RUN:" in code and "FULL_RUN = False" in code


def test_missing_hf_secret_stops_with_instructions():
    code = _code()
    assert "Add-ons" in code and "HF_TOKEN" in code and "raise SystemExit" in code


def test_workflow_pushes_waits_and_keeps_the_outputs():
    import yaml
    wf = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "kaggle-medgemma.yml").read_text())
    on = wf.get("on", wf.get(True))
    assert "workflow_dispatch" in on
    job = wf["jobs"]["run"]
    assert job["environment"] == "dev"
    text = (REPO_ROOT / ".github" / "workflows" / "kaggle-medgemma.yml").read_text()
    for step in ("prepare_kernel.py", "kaggle kernels push", "kaggle kernels status", "kaggle kernels output",
                 "upload-artifact"):
        assert step in text, step
    assert "--accelerator" in text
    assert "kaggle kernels list --mine" in text          # fails early, with instructions, on bad credentials
    assert 'tok="${T:-$K}"' in text                      # a new-style token saved as KAGGLE_KEY still works
