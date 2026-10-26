"""Databricks Asset Bundle: dev / uat / prod targets are complete and consistent.
(`databricks bundle validate` needs workspace auth; CI runs it per target.)"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
VAR = re.compile(r"\$\{var\.([a-z_]+)\}")
WIDGET = re.compile(r"""widgets\.(?:text|dropdown)\(\s*["']([a-z_]+)["']|CREATE WIDGET TEXT ([a-z_]+)""")


def _load():
    root = yaml.safe_load((ROOT / "databricks.yml").read_text())
    jobs = {}
    for inc in root.get("include", []):
        for f in ROOT.glob(inc):
            for k, j in yaml.safe_load(f.read_text())["resources"].get("jobs", {}).items():
                jobs[k] = (j, f.parent)
    return root, jobs


def _tasks(root, jobs):
    for name, (j, base) in jobs.items():
        for t in j["tasks"]:
            yield name, t, base
    for tgt in root["targets"].values():
        for name, j in tgt.get("resources", {}).get("jobs", {}).items():
            for t in j["tasks"]:
                yield name, t, ROOT


def test_three_targets_with_expected_modes():
    root, _ = _load()
    t = root["targets"]
    assert set(t) == {"dev", "uat", "prod"}
    assert t["dev"]["mode"] == "development" and t["dev"]["default"]
    for env in ("uat", "prod"):
        assert t[env]["mode"] == "production"
        assert "service_principal_name" in t[env]["run_as"]
        assert "/Shared/" in t[env]["workspace"]["root_path"]


def test_each_target_writes_to_its_own_catalog_schema():
    root, _ = _load()
    d = {k: v["default"] for k, v in root["variables"].items() if "default" in v}
    places = {env: (t.get("variables", {}).get("catalog", d["catalog"]),
                    t.get("variables", {}).get("schema", d["schema"])) for env, t in root["targets"].items()}
    assert len(set(places.values())) == 3, places


def test_every_variable_used_is_defined():
    root, _ = _load()
    defined = set(root["variables"])
    text = (ROOT / "databricks.yml").read_text() + "".join(
        f.read_text() for inc in root["include"] for f in ROOT.glob(inc))
    assert set(VAR.findall(text)) <= defined
    for env, t in root["targets"].items():
        assert set(t.get("variables", {})) <= defined, env


def test_notebooks_exist_and_take_the_parameters_passed():
    root, jobs = _load()
    seen = 0
    for name, task, base in _tasks(root, jobs):
        nb = (base / task["notebook_task"]["notebook_path"]).resolve()
        assert nb.exists(), f"{name}: {nb}"
        widgets = {a or b for a, b in WIDGET.findall(nb.read_text())}
        params = set(task["notebook_task"].get("base_parameters", {}))
        assert params <= widgets, f"{name}: {params - widgets} not widgets in {nb.name}"
        seen += 1
    assert seen >= 3


def test_medgemma_gpu_job_only_in_uat_and_prod():
    root, jobs = _load()
    assert "medgemma_reader" not in jobs
    for env in ("uat", "prod"):
        assert "medgemma_reader" in root["targets"][env]["resources"]["jobs"]


def test_mlflow_experiment_and_uc_model_per_target():
    m = yaml.safe_load((ROOT / "databricks/resources/mlops.yml").read_text())["resources"]
    assert "${bundle.target}" in "".join(m["experiments"]["dental_experiment"]["name"]) or \
        "${workspace.root_path}" in m["experiments"]["dental_experiment"]["name"]
    rm = m["registered_models"]["perio_note_classifier"]
    assert rm["catalog_name"] == "${var.catalog}" and rm["schema_name"] == "${var.schema}"


def test_study_benchmark_passes_experiment_id_not_name():
    """MLflow stores /Workspace/Users/... as /Users/..., so passing the name makes Terraform
    see a changed value mid-apply ("Provider produced inconsistent final plan")."""
    _, jobs = _load()
    params = jobs["study_benchmark"][0]["tasks"][0]["notebook_task"]["base_parameters"]
    assert params.get("experiment_id") == "${resources.experiments.dental_experiment.id}"
    assert "experiment" not in params


def test_judge_monitoring_job_only_in_uat_and_prod():
    """Production monitoring scores live traces, so it exists where there is live traffic."""
    root, jobs = _load()
    assert "judge_monitoring" not in jobs and "judge_monitoring" not in root["targets"]["dev"].get("resources", {}).get("jobs", {})
    for env in ("uat", "prod"):
        t = root["targets"][env]["resources"]["jobs"]["judge_monitoring"]["tasks"][0]["notebook_task"]
        assert t["base_parameters"]["experiment_id"] == "${resources.experiments.dental_experiment.id}"
        assert t["base_parameters"]["sample_rate"] == "${var.judge_sample_rate}"
