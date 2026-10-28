"""The Kaggle MedGemma notebook stays runnable: valid notebook, flags the script really has, no secrets."""

import json
import re

from health_transformation_lab_nlp.paths import REPO_ROOT

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


def test_notebook_needs_no_hugging_face_token():
    # a notebook pushed by `kaggle kernels push` can't read Kaggle Secrets, so the weights come from Kaggle Models
    code = _code()
    assert "UserSecretsClient" not in code and "HF_TOKEN" not in code
    assert not re.search(r"hf_[A-Za-z0-9]{20,}", NB.read_text())


def test_notebook_converts_the_kaggle_model_and_reads_it_locally():
    code = _code()
    convert = code.index("kaggle/keras_to_hf.py")
    reads = [m.start() for m in re.finditer(r"11_ai_predict\.py", code)]
    assert reads and all(convert < i for i in reads)
    for line in re.findall(r"11_ai_predict\.py[^\n]*", code):
        assert "--weights {WEIGHTS}" in line, line
    assert 'WEIGHTS = "/kaggle/temp/' in code           # outside /kaggle/working: not kept as output


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
    _, meta, nb = _prepare(tmp_path, "--limit", "5", "--shots", "2", "--branch", "dev-x")
    assert meta["id"] == "someone/health-transformation-lab-medgemma-reader" and meta["code_file"] == "medgemma_reader.ipynb"
    assert meta["enable_gpu"] is True and meta["enable_internet"] is True
    assert meta["is_private"] is False          # public: synthetic notes only, and no token anywhere
    assert meta["kernel_type"] == "notebook" and meta["language"] == "python"
    s = _settings(nb)
    assert 'RUNG = "medgemma-1.5-4b-it"' in s and "TEST_NOTES = 5" in s and "SHOTS = 2" in s
    assert 'BRANCH = "dev-x"' in s and "FULL_RUN = False" in s


def test_default_rung_attaches_medgemma_1_5_from_kaggle_models(tmp_path):
    _, meta, _ = _prepare(tmp_path)
    assert meta["model_sources"] == ["keras/medgemma/keras/medgemma_1.5_instruct_4b/1"]


def test_rung_without_a_kaggle_model_is_refused(tmp_path):
    import subprocess
    import sys
    r = subprocess.run([sys.executable, str(REPO_ROOT / "kaggle" / "prepare_kernel.py"), "--out", str(tmp_path / "k"),
                        "--username", "someone", "--rung", "medgemma-4b-it"], capture_output=True, text=True, check=False)
    assert r.returncode != 0 and "kaggle" in r.stderr


def test_limit_zero_means_the_full_run(tmp_path):
    _, _, nb = _prepare(tmp_path, "--limit", "0")
    assert "FULL_RUN = True" in _settings(nb)


def test_full_run_cell_only_runs_when_asked():
    code = _code()
    assert "if FULL_RUN:" in code and "FULL_RUN = False" in code


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


def test_repo_is_cloned_outside_the_output_folder():
    # /kaggle/working is what Kaggle keeps as output: a clone there came back as 464 files
    code = _code()
    assert 'REPO = "/kaggle/temp/health-transformation-lab-nlp"' in code
    assert "health-transformation-lab-nlp/python" not in code.replace("{REPO}/python", "")


def test_show_log_prints_the_notebook_output_without_warnings(tmp_path):
    import subprocess
    import sys
    log = tmp_path / "k.log"
    log.write_text(json.dumps([
        {"stream_name": "stdout", "time": 1.0, "data": "ready\n"},
        {"stream_name": "stderr", "time": 2.0, "data": "/x/mistune.py:435: SyntaxWarning: invalid escape\n  cells = re.sub(a, b)\n"},
        {"stream_name": "stderr", "time": 2.5, "data": "FutureWarning: one line, no source\n"},
        {"stream_name": "stdout", "time": 3.0, "data": "loading /kaggle/temp/medgemma-hf as float32\n"},
        {"stream_name": "stderr", "time": 4.0, "data": "[NbConvertApp] Writing 1 bytes\n"},
    ]))
    out = subprocess.run([sys.executable, str(REPO_ROOT / "kaggle" / "show_log.py"), str(log)],
                         check=True, capture_output=True, text=True).stdout
    assert "ready" in out and "loading /kaggle/temp/medgemma-hf" in out
    assert "SyntaxWarning" not in out and "re.sub" not in out and "NbConvertApp" not in out
    wf = (REPO_ROOT / ".github" / "workflows" / "kaggle-medgemma.yml").read_text()
    assert "kaggle/show_log.py" in wf


# ---- Kaggle Models ships MedGemma as a Keras preset: kaggle/keras_to_hf.py turns it into a transformers folder

def _converter():
    import importlib.util
    spec = importlib.util.spec_from_file_location("keras_to_hf", REPO_ROOT / "kaggle" / "keras_to_hf.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_kaggle_rung_ships_googles_config():
    import yaml
    reg = yaml.safe_load((REPO_ROOT / "models.yaml").read_text())
    on_kaggle = [m for m in reg["models"] if m.get("kaggle")]
    assert [m["id"] for m in on_kaggle] == ["medgemma-1.5-4b-it"]
    for m in on_kaggle:
        assert re.fullmatch(r"keras/medgemma/keras/[a-z0-9_.]+/\d+", m["kaggle"]), m["id"]
        cfg = json.loads((REPO_ROOT / "kaggle" / "hf_config" / f"{m['id']}.config.json").read_text())
        assert cfg["architectures"] == ["Gemma3ForConditionalGeneration"]
        assert cfg["text_config"]["rope_scaling"] == {"factor": 8.0, "rope_type": "linear"}   # read by transformers 4.x


def test_finished_checkpoint_has_googles_configs_and_medgemmas_chat_template(tmp_path):
    # the Keras exporter writes no chat template, no stop tokens and a transformers-5-only config
    (tmp_path / "tokenizer_config.json").write_text(json.dumps({"tokenizer_class": "GemmaTokenizer"}))
    (tmp_path / "config.json").write_text(json.dumps({"text_config": {"rope_parameters": {}}}))
    (tmp_path / "generation_config.json").write_text(json.dumps({"eos_token_id": 1}))
    _converter().finish(tmp_path, "medgemma-1.5-4b-it")
    google = REPO_ROOT / "kaggle" / "hf_config"
    assert (tmp_path / "config.json").read_text() == (google / "medgemma-1.5-4b-it.config.json").read_text()
    template = (REPO_ROOT / "kaggle" / "gemma3_chat_template.jinja").read_text()
    assert "<start_of_turn>" in template
    assert json.loads((tmp_path / "tokenizer_config.json").read_text())["chat_template"] == template
    assert json.loads((tmp_path / "chat_template.json").read_text())["chat_template"] == template
    assert (tmp_path / "chat_template.jinja").read_text() == template
    assert json.loads((tmp_path / "generation_config.json").read_text())["eos_token_id"] == [1, 106]


def test_converter_finds_the_model_from_the_rung():
    assert _converter().kaggle_handle("medgemma-1.5-4b-it") == "keras/medgemma/keras/medgemma_1.5_instruct_4b/1"


# ---- the notebook runs the commit the workflow was started from, not whatever a branch points to later

def test_prepared_kernel_pins_the_commit(tmp_path):
    sha = "e1455e441245fb86b27ccb54e3db4f1fba51b2f2"
    _, _, nb = _prepare(tmp_path, "--branch", "claude/x", "--commit", sha)
    assert f'COMMIT = "{sha}"' in _settings(nb)


def test_prepared_kernel_without_a_commit_follows_the_branch(tmp_path):
    _, _, nb = _prepare(tmp_path)
    assert 'COMMIT = ""' in _settings(nb) and 'BRANCH = "main"' in _settings(nb)


def test_notebook_checks_out_the_pinned_commit_and_says_which_code_it_runs():
    code = _code()
    assert "if COMMIT:" in code and "fetch --quiet --depth 1 origin {COMMIT}" in code
    assert "log -1" in code                               # prints branch, short sha and date of the code it runs
    assert code.index("log -1") < code.index("11_ai_predict.py")


def test_workflow_defaults_to_the_branch_and_commit_it_was_started_from():
    import yaml
    path = REPO_ROOT / ".github" / "workflows" / "kaggle-medgemma.yml"
    wf = yaml.safe_load(path.read_text())
    inputs = wf.get("on", wf.get(True))["workflow_dispatch"]["inputs"]
    assert inputs["branch"]["default"] == ""             # empty: the branch picked in "Use workflow from"
    text = path.read_text()
    assert "inputs.branch || github.ref_name" in text
    assert "github.sha" in text                          # pinned when it runs its own branch
