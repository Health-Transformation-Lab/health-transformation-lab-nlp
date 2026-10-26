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
                 "CREATE_CATALOG", "ALL_PRIVILEGES", "put-acl"):
        assert need in text, need
    # the secret is made by hand and goes straight into GitHub: the script only prints the command
    code, printed = text.split("cat <<EOF")
    assert "service-principal-secrets-proxy" not in code and "service-principal-secrets-proxy create" in printed


@pytest.mark.skipif(not shutil.which("bash"), reason="no bash")
@pytest.mark.parametrize("target", ["dev", "uat", "prod"])
def test_script_reads_catalog_schema_and_scope_from_the_bundle(target):
    """--print-config prints what the script would use for a target, without a workspace."""
    out = subprocess.run(["bash", str(SCRIPT), target, "--print-config"],
                         capture_output=True, text=True, check=True).stdout.split()
    b = yaml.safe_load((ROOT / "databricks.yml").read_text())
    v = {k: x.get("default") for k, x in b["variables"].items()}
    v.update(b["targets"][target].get("variables", {}))
    assert out == [f"dental_omop_nlp_{target}_sp", f"dental_omop_nlp_{target}_admin",
                   v["catalog"], v["schema"], v["hf_secret_scope"]]


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
