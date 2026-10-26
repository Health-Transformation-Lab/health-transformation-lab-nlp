"""Create the service principal that deploys and runs the uat/prod bundle targets.

A bundle can't create a service principal, so this does it with the Databricks SDK:
the principal, its entitlements, and the grants the jobs need (catalog and schema,
SQL warehouse, judge serving endpoint, the secret scope). Settings come from the
target in databricks.yml, like `bundle deploy` would read them. `plan` is pure;
`apply` talks to the workspace and skips what doesn't exist yet. Guide:
docs/deployment.md. Script: scripts/32_service_principal.py.
"""

from __future__ import annotations

import os

import yaml

from dental_omop_nlp.paths import REPO_ROOT

try:
    from databricks.sdk.errors import NotFound
except ImportError:  # SDK only needed for apply
    class NotFound(Exception):
        pass

ENTITLEMENTS = ("workspace-access", "allow-cluster-create")   # notebooks + the MedGemma GPU job cluster
CATALOG_PRIVILEGES = ("USE_CATALOG", "CREATE_SCHEMA")         # notebooks run CREATE SCHEMA IF NOT EXISTS
SCHEMA_PRIVILEGES = ("USE_SCHEMA", "SELECT", "MODIFY", "CREATE_TABLE", "CREATE_VOLUME",
                     "READ_VOLUME", "WRITE_VOLUME", "CREATE_MODEL")
OAUTH_SCOPES = ["all-apis"]                                   # what the Databricks CLI asks for
SETTINGS = ("catalog", "schema", "warehouse_name", "judge_endpoint", "hf_secret_scope")


def target_settings(target: str, overrides: dict | None = None, root=REPO_ROOT) -> dict:
    """Bundle variables for one target: default < target < BUNDLE_VAR_<name> < overrides."""
    b = yaml.safe_load((root / "databricks.yml").read_text())
    t = b["targets"][target]
    out = {}
    for k in SETTINGS:
        v = t.get("variables", {}).get(k, b["variables"][k].get("default"))
        v = os.environ.get(f"BUNDLE_VAR_{k}", v)
        if overrides and overrides.get(k) is not None:
            v = overrides[k]
        out[k] = v
    out["secret_scope"] = out.pop("hf_secret_scope")
    return out


def plan(target: str, *, display_name: str | None = None, overrides: dict | None = None,
         create_secret: bool = False, root=REPO_ROOT) -> list[dict]:
    s = target_settings(target, overrides, root)
    steps = [{"action": "service_principal", "display_name": display_name or f"dental-omop-nlp-{target}",
              "entitlements": list(ENTITLEMENTS)},
             {"action": "grant_catalog", "name": s["catalog"], "privileges": list(CATALOG_PRIVILEGES)},
             {"action": "grant_schema", "name": f"{s['catalog']}.{s['schema']}",
              "privileges": list(SCHEMA_PRIVILEGES)},
             {"action": "warehouse", "name": s["warehouse_name"], "level": "CAN_USE"}]
    if s["judge_endpoint"] and s["judge_endpoint"] != "none":
        steps.append({"action": "serving_endpoint", "name": s["judge_endpoint"], "level": "CAN_QUERY"})
    steps.append({"action": "secret_scope", "name": s["secret_scope"], "level": "READ"})
    if create_secret:
        steps.append({"action": "oauth_secret", "scopes": list(OAUTH_SCOPES)})
    return steps


def describe(steps: list[dict]) -> str:
    lines = []
    for s in steps:
        a = s["action"]
        if a == "service_principal":
            lines.append(f"service principal {s['display_name']!r} (create if missing), "
                         f"entitlements: {', '.join(s['entitlements'])}")
        elif a in ("grant_catalog", "grant_schema"):
            lines.append(f"{a.split('_')[1]} {s['name']}: {', '.join(s['privileges'])}")
        elif a == "oauth_secret":
            lines.append(f"OAuth secret, scopes: {', '.join(s['scopes'])} (Databricks shows it once; saved to a 0600 file)")
        else:
            lines.append(f"{a.replace('_', ' ')} {s['name']}: {s['level']}")
    return "\n".join(lines)


def apply(steps: list[dict], w) -> dict:
    """Run the plan with a databricks.sdk.WorkspaceClient. Re-running is safe: an existing
    principal (same display name) is reused and grants are additive."""
    from databricks.sdk.service import catalog, iam, serving, sql, workspace

    head = steps[0]
    found = list(w.service_principals.list(filter=f'displayName eq "{head["display_name"]}"'))
    created = not found
    p = found[0] if found else w.service_principals.create(
        display_name=head["display_name"], active=True,
        entitlements=[iam.ComplexValue(value=e) for e in head["entitlements"]])
    app = p.application_id
    out = {"application_id": app, "id": p.id, "created": created, "secret": None, "skipped": []}

    for s in steps[1:]:
        a = s["action"]
        if a in ("grant_catalog", "grant_schema"):
            kind = a.split("_")[1]
            if kind == "schema":
                try:
                    w.schemas.get(s["name"])
                except NotFound:
                    out["skipped"].append(f"{a}: {s['name']} doesn't exist yet; the first job run creates "
                                          "it as the service principal, which then owns it")
                    continue
            w.grants.update(kind, s["name"], changes=[catalog.PermissionsChange(
                principal=app, add=[catalog.Privilege(x) for x in s["privileges"]])])
        elif a == "warehouse":
            wh = next((x for x in w.warehouses.list() if x.name == s["name"]), None)
            if wh is None:
                out["skipped"].append(f"{a}: no SQL warehouse named {s['name']!r}")
                continue
            w.warehouses.update_permissions(wh.id, access_control_list=[sql.WarehouseAccessControlRequest(
                service_principal_name=app, permission_level=sql.WarehousePermissionLevel(s["level"]))])
        elif a == "serving_endpoint":
            try:
                ep = w.serving_endpoints.get(s["name"])
            except NotFound:
                out["skipped"].append(f"{a}: no serving endpoint {s['name']!r}")
                continue
            w.serving_endpoints.update_permissions(ep.id, access_control_list=[
                serving.ServingEndpointAccessControlRequest(
                    service_principal_name=app,
                    permission_level=serving.ServingEndpointPermissionLevel(s["level"]))])
        elif a == "secret_scope":
            if s["name"] not in {x.name for x in w.secrets.list_scopes()}:
                out["skipped"].append(f"{a}: no secret scope {s['name']!r}; create it, then re-run")
                continue
            w.secrets.put_acl(s["name"], app, workspace.AclPermission(s["level"]))
        elif a == "oauth_secret":
            out["secret"] = w.service_principal_secrets_proxy.create(p.id, scopes=s["scopes"]).secret
    return out
