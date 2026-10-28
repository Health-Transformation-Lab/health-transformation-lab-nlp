#!/usr/bin/env bash
# Deploy the bundle to one target (deploy.yml). Usage: deploy_bundle.sh <target>
#
# A Genie space (spec 019) can't be created until its tables exist, and the tables are written by the
# Load results job, which this deploy creates. So the first deploy into a catalog without them fails on the
# Genie spaces alone (issue #154). When that is the only reason, run Load results, wait for it, and deploy
# again. Any other failure fails the step. Writes loaded=true|false to $GITHUB_OUTPUT so the workflow
# doesn't start Load results a second time.
set -uo pipefail
target="${1:?usage: deploy_bundle.sh <target>}"
out="${GITHUB_OUTPUT:-/dev/null}"
log="$(mktemp)"
trap 'rm -f "$log"' EXIT

if databricks bundle deploy -t "$target" 2>&1 | tee "$log"; then
  echo "loaded=false" >> "$out"
  exit 0
fi

if grep -q "genie_spaces" "$log" && grep -q "does not exist" "$log"; then
  echo "A Genie space's tables don't exist yet: running Load results, then deploying again (issue #154)."
  databricks bundle run -t "$target" load_results || { echo "Load results failed; see the run above." >&2; exit 1; }
  databricks bundle deploy -t "$target" || exit 1
  echo "loaded=true" >> "$out"
  exit 0
fi

exit 1
