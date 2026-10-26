"""Databricks Asset Bundle: dev / uat / prod targets are complete and consistent.
(`databricks bundle validate` needs workspace auth; CI runs it per target.)"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
VAR = re.compile(r"\$\{var\.([a-z_]+)\}")
GOLD_CATALOG = "${resources.schemas.gold.catalog_name}"
GOLD_SCHEMA = "${resources.schemas.gold.name}"
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
    # No development mode in dev: it prefixes every name ([dev <user>] jobs,
    # dev_<user>_ catalogs/schemas/models). The workspace separates environments.
    assert "mode" not in t["dev"] and t["dev"]["default"]
    assert t["dev"]["presets"] == {"trigger_pause_status": "PAUSED"}
    assert "name_prefix" not in root.get("presets", {})
    for env in ("uat", "prod"):
        assert t[env]["mode"] == "production"
        assert "service_principal_name" in t[env]["run_as"]
        assert "/Shared/" in t[env]["workspace"]["root_path"]


def test_every_target_uses_the_same_catalog_and_domain():
    # dev, uat and prod are separate workspaces, so the Unity Catalog names are the
    # same everywhere: catalog dental_omop, schemas <layer>_dental_omop_perio.
    root, _ = _load()
    d = {k: v["default"] for k, v in root["variables"].items() if "default" in v}
    places = {env: (t.get("variables", {}).get("catalog", d["catalog"]),
                    t.get("variables", {}).get("domain", d["domain"])) for env, t in root["targets"].items()}
    assert set(places.values()) == {("dental_omop", "dental_omop_perio")}, places


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
    assert rm["catalog_name"] == GOLD_CATALOG and rm["schema_name"] == GOLD_SCHEMA


def test_judge_monitoring_job_only_in_uat_and_prod():
    """Production monitoring scores live traces, so it exists where there is live traffic."""
    root, jobs = _load()
    assert "judge_monitoring" not in jobs and "judge_monitoring" not in root["targets"]["dev"].get("resources", {}).get("jobs", {})
    for env in ("uat", "prod"):
        t = root["targets"][env]["resources"]["jobs"]["judge_monitoring"]["tasks"][0]["notebook_task"]
        assert t["base_parameters"]["experiment_id"] == "${resources.experiments.dental_experiment.id}"
        assert t["base_parameters"]["sample_rate"] == "${var.judge_sample_rate}"


def test_bundle_creates_the_catalog_layer_schemas_and_landing_volume():
    """One catalog (dental_omop) with landing / bronze / silver / gold schemas, all
    bundle resources so a deploy creates them; the data volume lives in landing.
    prevent_destroy keeps `bundle destroy` from dropping data."""
    uc = yaml.safe_load((ROOT / "databricks/resources/unity_catalog.yml").read_text())["resources"]
    assert {k: c["name"] for k, c in uc["catalogs"].items()} == {"dental_omop": "${var.catalog}"}
    layers = ("landing", "bronze", "silver", "gold")
    assert {k: sc["name"] for k, sc in uc["schemas"].items()} == {k: f"{k}_${{var.domain}}" for k in layers}
    assert {sc["catalog_name"] for sc in uc["schemas"].values()} == {"${resources.catalogs.dental_omop.name}"}
    vol = uc["volumes"]["data"]
    assert vol["catalog_name"] == "${resources.schemas.landing.catalog_name}"
    assert vol["schema_name"] == "${resources.schemas.landing.name}" and vol["volume_type"] == "MANAGED"
    for r in [*uc["catalogs"].values(), *uc["schemas"].values(), vol]:
        assert r["lifecycle"]["prevent_destroy"] is True


def test_jobs_write_to_the_bundle_schema():
    # Via the resource, not ${var.catalog}, so a deploy creates the schema before
    # any job that writes to it.
    root, jobs = _load()
    seen = 0
    for name, task, _ in _tasks(root, jobs):
        p = task["notebook_task"].get("base_parameters", {})
        if "catalog" in p:
            assert (p["catalog"], p["schema"]) == (GOLD_CATALOG, GOLD_SCHEMA), name
            seen += 1
        if "landing_schema" in p:
            assert p["landing_schema"] == "${resources.volumes.data.schema_name}", name
    assert seen >= 3
    bench = jobs["study_benchmark"][0]["tasks"][0]["notebook_task"]["base_parameters"]
    assert bench["landing_schema"] == "${resources.volumes.data.schema_name}"


def test_encoder_rung_off_in_dev_on_in_uat_and_prod():
    """Dev is a quick smoke test: no DistilBERT fine-tune, no torch install."""
    root, jobs = _load()
    bench = jobs["study_benchmark"][0]["tasks"][0]["notebook_task"]["base_parameters"]
    assert bench["run_encoder"] == "${var.run_encoder}"
    d = root["variables"]["run_encoder"]["default"]
    got = {env: t.get("variables", {}).get("run_encoder", d) for env, t in root["targets"].items()}
    assert got == {"dev": "false", "uat": "true", "prod": "true"}


def test_benchmark_notebook_installs_cpu_torch_only_for_the_encoder():
    nb = (ROOT / "databricks/notebooks/01_run_benchmark.py").read_text()
    assert "download.pytorch.org/whl/cpu" in nb
    assert 'if run_encoder:\n    results.append(run("distilbert-base"' in nb


def test_deploy_does_not_wait_for_the_benchmark_run():
    wf = (ROOT / ".github/workflows/deploy.yml").read_text()
    assert "bundle run -t \"$TARGET\" --no-wait study_benchmark" in wf
