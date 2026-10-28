"""The Kaggle encoder notebook (spec 002 T017 on a free GPU, issue #84): same rungs and learning rates as the
Databricks encoder_gpu job, the workflow's commit, no token, and results that reach the gold tables."""

import json
import re
import subprocess
import sys

import yaml

from health_transformation_lab_nlp.paths import REPO_ROOT

NB = REPO_ROOT / "kaggle" / "encoder_gpu.ipynb"
WF = REPO_ROOT / ".github" / "workflows" / "kaggle-encoders.yml"


def _code():
    nb = json.loads(NB.read_text())
    assert nb["nbformat"] == 4
    return "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")


def _prepare(tmp_path, *extra):
    out = tmp_path / "kernel"
    subprocess.run([sys.executable, str(REPO_ROOT / "kaggle" / "prepare_kernel.py"), "--job", "encoders",
                    "--out", str(out), "--username", "someone", *extra], check=True)
    nb = json.loads((out / "encoder_gpu.ipynb").read_text())
    settings = "".join(next(c["source"] for c in nb["cells"] if "BRANCH =" in "".join(c["source"])))
    return json.loads((out / "kernel-metadata.json").read_text()), settings


def _bundle_default(name):
    return yaml.safe_load((REPO_ROOT / "databricks.yml").read_text())["variables"][name]["default"]


def test_notebook_runs_the_training_script_with_flags_it_has():
    script = (REPO_ROOT / "python" / "scripts" / "11_ai_predict.py").read_text()
    lines = re.findall(r"11_ai_predict\.py[^\n]*", _code())
    assert lines
    for flag in ("--rung", "--epochs", "--max-len", "--lr", "--limit"):
        assert f'"{flag}"' in script and flag in _code(), flag


def test_notebook_needs_no_token_and_clones_outside_the_output_folder():
    code = _code()
    assert "UserSecretsClient" not in code and "HF_TOKEN" not in code
    assert 'REPO = "/kaggle/temp/health-transformation-lab-nlp"' in code
    assert "if COMMIT:" in code and "log -1" in code


def test_notebook_keeps_going_past_a_failed_rung_and_fails_at_the_end():
    code = _code()
    assert "failed.append(rung)" in code and "raise RuntimeError" in code
    assert code.index("/kaggle/working") < code.index("raise RuntimeError")   # the good rungs are saved first


def test_every_rung_the_databricks_job_runs_is_public_on_hugging_face():
    reg = {m["id"]: m for m in yaml.safe_load((REPO_ROOT / "models.yaml").read_text())["models"]}
    for rung in _bundle_default("encoder_gpu_rungs").split(","):
        assert reg[rung]["hf"], rung


def test_prepared_kernel_matches_the_databricks_job_by_default(tmp_path):
    meta, s = _prepare(tmp_path, "--commit", "abc123")
    assert meta["id"] == "someone/dental-omop-encoder-gpu" and meta["code_file"] == "encoder_gpu.ipynb"
    assert meta["enable_gpu"] is True and meta["enable_internet"] is True and meta["is_private"] is False
    assert meta["model_sources"] == []                       # weights come from Hugging Face, no token
    assert f'RUNGS = "{_bundle_default("encoder_gpu_rungs")}"' in s
    assert f'LR_OVERRIDES = "{_bundle_default("encoder_gpu_lr")}"' in s
    assert "EPOCHS = 3" in s and "MAX_LEN = 256" in s and "FULL_RUN = False" in s
    assert 'COMMIT = "abc123"' in s


def test_limit_zero_is_the_full_run(tmp_path):
    _, s = _prepare(tmp_path, "--limit", "0", "--rungs", "gatortron-base", "--epochs", "2")
    assert "FULL_RUN = True" in s and 'RUNGS = "gatortron-base"' in s and "EPOCHS = 2" in s


def test_test_run_reads_a_few_notes_with_one_epoch():
    code = _code()
    assert "if FULL_RUN" in code and '"--limit", str(TEST_NOTES)' in code and '"--epochs", "1"' in code


def test_workflow_pushes_the_encoder_kernel_waits_and_opens_a_results_pr():
    wf = yaml.safe_load(WF.read_text())
    on = wf.get("on", wf.get(True))
    inputs = on["workflow_dispatch"]["inputs"]
    assert inputs["rungs"]["default"] == _bundle_default("encoder_gpu_rungs")
    assert inputs["lr_overrides"]["default"] == _bundle_default("encoder_gpu_lr")
    assert inputs["branch"]["default"] == ""
    assert wf["jobs"]["run"]["environment"] == "dev"
    text = WF.read_text()
    for step in ("prepare_kernel.py --job encoders", "kaggle kernels push", "kaggle kernels status",
                 "kaggle kernels output", "kaggle/show_log.py", "kaggle/record_results.py", "upload-artifact",
                 "kaggle kernels list --mine", 'tok="${T:-$K}"', "inputs.branch || github.ref_name", "github.sha"):
        assert step in text, step
    assert "/dental-omop-encoder-gpu" in text


def test_medgemma_is_still_the_default_job(tmp_path):
    out = tmp_path / "k"
    subprocess.run([sys.executable, str(REPO_ROOT / "kaggle" / "prepare_kernel.py"), "--out", str(out),
                    "--username", "someone"], check=True)
    assert (out / "medgemma_reader.ipynb").exists() and not (out / "encoder_gpu.ipynb").exists()
