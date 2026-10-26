"""Create the service principal for a bundle target and grant what its jobs use (docs/deployment.md).

    databricks auth login --host https://<workspace>        # as a workspace admin, once
    python scripts/32_service_principal.py --target uat                     # dry run: prints the plan
    python scripts/32_service_principal.py --target uat --apply             # create + grant
    python scripts/32_service_principal.py --target uat --apply --create-secret

Settings come from the target in databricks.yml (and BUNDLE_VAR_<name>, as CI passes them).
Safe to re-run: an existing principal with the same name is reused and grants are additive.
--create-secret writes DATABRICKS_HOST / CLIENT_ID / CLIENT_SECRET to a 0600 file (gitignored)
for you to copy into the GitHub environment's secrets; the secret is never printed.
Needs `pip install -e ".[databricks]"` for --apply.
"""

import argparse
import os
from pathlib import Path

from dental_omop_nlp import service_principal as sp
from dental_omop_nlp.paths import REPO_ROOT

ap = argparse.ArgumentParser()
ap.add_argument("--target", required=True, choices=["dev", "uat", "prod"])
ap.add_argument("--display-name", help="default dental-omop-nlp-<target>")
ap.add_argument("--profile", help="Databricks CLI profile (default: DEFAULT / environment)")
ap.add_argument("--warehouse-name")
ap.add_argument("--judge-endpoint")
ap.add_argument("--apply", action="store_true", help="make the changes (default: print the plan)")
ap.add_argument("--create-secret", action="store_true", help="also create an OAuth M2M secret")
ap.add_argument("--secret-file", type=Path, help="default .databricks-sp-<target>.env at the repo root")
a = ap.parse_args()

steps = sp.plan(a.target, display_name=a.display_name, create_secret=a.create_secret,
                overrides={"warehouse_name": a.warehouse_name, "judge_endpoint": a.judge_endpoint})
print(f"target {a.target}:\n" + sp.describe(steps))
if not a.apply:
    print("\ndry run; pass --apply to make these changes")
    raise SystemExit(0)

from databricks.sdk import WorkspaceClient

w = WorkspaceClient(profile=a.profile) if a.profile else WorkspaceClient()
out = sp.apply(steps, w)
print(f"\n{'created' if out['created'] else 'reused'} service principal; application id {out['application_id']}")
for s in out["skipped"]:
    print("skipped", s)
print(f"\nGitHub environment {a.target!r}: variable SERVICE_PRINCIPAL = {out['application_id']}")
if out["secret"]:
    path = a.secret_file or REPO_ROOT / f".databricks-sp-{a.target}.env"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(f"DATABRICKS_HOST={w.config.host}\nDATABRICKS_CLIENT_ID={out['application_id']}\n"
                f"DATABRICKS_CLIENT_SECRET={out['secret']}\n")
    print(f"secrets DATABRICKS_HOST, DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET written to {path}\n"
          "copy them into the GitHub environment, then delete the file")
