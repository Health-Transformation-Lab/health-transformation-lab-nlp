"""databricks/setup/create_service_principal.sh and the workflows that sign in as its principal.
(The script itself needs a workspace; these check what can be checked without one.)"""

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "databricks" / "setup" / "create_service_principal.sh"


def test_script_is_valid_bash_and_strict():
    text = SCRIPT.read_text()
    assert text.startswith("#!/usr/bin/env bash") and "set -euo pipefail" in text
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)


def test_script_grants_what_a_deploy_as_the_principal_needs():
    text = SCRIPT.read_text()
    for need in ("workspace-access", "databricks-sql-access",   # workspace APIs; warehouse lookup
                 "CREATE_CATALOG", "put-acl"):
        assert need in text, need
    # the bundle creates the catalog, schemas and volume (unity_catalog.yml); a catalog
    # made here first would make the deploy fail on "already exists"
    assert "catalogs create" not in text and "schemas create" not in text
    # the secret is made by hand and goes straight into GitHub: the script only prints the command
    code, printed = text.split("cat <<EOF")
    assert "service-principal-secrets-proxy" not in code and "service-principal-secrets-proxy create" in printed


@pytest.mark.skipif(not shutil.which("bash"), reason="no bash")
@pytest.mark.parametrize("target", ["dev", "uat", "prod"])
def test_script_reads_names_and_scope_from_the_bundle(target):
    """--print-config prints what the script would use for a target, without a workspace."""
    out = subprocess.run(["bash", str(SCRIPT), target, "--print-config"],
                         capture_output=True, text=True, check=True).stdout.split()
    b = yaml.safe_load((ROOT / "databricks.yml").read_text())
    v = {k: x.get("default") for k, x in b["variables"].items()}
    v.update(b["targets"][target].get("variables", {}))
    assert out == [f"dental_omop_nlp_{target}_sp", f"dental_omop_nlp_{target}_admin",
                   v["catalog"], v["hf_secret_scope"]]


def test_unknown_target_is_refused():
    r = subprocess.run(["bash", str(SCRIPT), "staging", "--print-config"], capture_output=True, text=True,
                       check=False)
    assert r.returncode != 0 and "staging" in r.stderr


@pytest.mark.parametrize("wf", ["ci.yml", "deploy.yml", "auth_check.yml"])
def test_workflows_read_host_and_client_id_as_variables(wf):
    """Host and client ID are identifiers (GitHub variables); only the client secret is a secret.
    A secret fallback keeps environments set up the older way working."""
    text = (ROOT / ".github" / "workflows" / wf).read_text()
    assert "${{ vars.DATABRICKS_HOST || secrets.DATABRICKS_HOST }}" in text
    assert "${{ vars.DATABRICKS_CLIENT_ID || secrets.DATABRICKS_CLIENT_ID }}" in text
    assert "${{ secrets.DATABRICKS_CLIENT_SECRET }}" in text


@pytest.mark.parametrize("wf", ["ci.yml", "deploy.yml"])
def test_databricks_steps_wait_for_the_client_secret(wf):
    """A host alone (set before the principal exists) must skip, not fail on sign-in."""
    text = (ROOT / ".github" / "workflows" / wf).read_text()
    assert "env.DATABRICKS_HOST != ''" not in text and "env.DATABRICKS_HOST == ''" not in text
    assert "env.DATABRICKS_CLIENT_SECRET != ''" in text


SIGNIN = ROOT / ".github" / "actions" / "databricks-signin" / "action.yml"


@pytest.mark.parametrize("wf", ["ci.yml", "deploy.yml", "auth_check.yml"])
def test_databricks_credentials_only_reach_the_cli_trimmed(wf):
    """Raw values never sit in a job's env; the sign-in action trims them before any databricks step."""
    doc = yaml.safe_load((ROOT / ".github" / "workflows" / wf).read_text())
    for name, job in doc["jobs"].items():
        steps = job.get("steps", [])
        uses_cli = [i for i, s in enumerate(steps) if "databricks " in s.get("run", "")]
        if not uses_cli:
            continue
        for scope in [job.get("env", {}), *(s.get("env", {}) for s in steps)]:
            assert not {"DATABRICKS_HOST", "DATABRICKS_CLIENT_ID", "DATABRICKS_CLIENT_SECRET"} & set(scope), name
        signin = [i for i, s in enumerate(steps) if s.get("uses") == "./.github/actions/databricks-signin"]
        assert signin and signin[0] < min(uses_cli), name


@pytest.mark.skipif(not shutil.which("bash"), reason="no bash")
def test_signin_action_strips_pasted_whitespace_and_masks_the_secret(tmp_path):
    """A value pasted from Windows ends in \\r\\n; sent as is, sign-in fails with invalid_client."""
    step = yaml.safe_load(SIGNIN.read_text())["runs"]["steps"][0]
    out = tmp_path / "github_env"
    r = subprocess.run(["bash", "-c", step["run"]], capture_output=True, text=True, check=True,
                       env={"PATH": "/usr/bin:/bin", "GITHUB_ENV": str(out),
                            "IN_HOST": " https://example.cloud.databricks.com/\r\n",
                            "IN_CLIENT_ID": "b0a70ecf-0000\r\n", "IN_CLIENT_SECRET": "dose123 \r\n"})
    assert dict(line.split("=", 1) for line in out.read_text().splitlines()) == {
        "DATABRICKS_HOST": "https://example.cloud.databricks.com",
        "DATABRICKS_CLIENT_ID": "b0a70ecf-0000", "DATABRICKS_CLIENT_SECRET": "dose123"}
    assert "::add-mask::dose123" in r.stdout


def test_actions_run_on_node_24():
    """checkout@v4 and setup-python@v5 run on Node 20, which GitHub has deprecated."""
    for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
        text = wf.read_text()
        assert "actions/checkout@v4" not in text and "actions/setup-python@v5" not in text, wf.name
