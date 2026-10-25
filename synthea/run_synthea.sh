#!/usr/bin/env bash
# Generate a small synthetic population with Synthea, dental modules only.
#
#   ./synthea/run_synthea.sh [N_PATIENTS] [SEED]
#
# Defaults: 500 patients, seed 42. Output lands in synthea/output/csv/.
# Needs Java 11+. Downloads synthea-with-dependencies.jar on first run.
set -euo pipefail

N=${1:-500}
SEED=${2:-42}
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JAR="$HERE/synthea-with-dependencies.jar"
JAR_URL="https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar"
OUT="$HERE/output"

if ! command -v java >/dev/null; then
  echo "Java 11+ is required (java not found on PATH)." >&2
  exit 1
fi

if [[ ! -f "$JAR" ]]; then
  echo "Downloading Synthea jar..."
  curl -fL --retry 3 -o "$JAR" "$JAR_URL"
fi

rm -rf "$OUT"
mkdir -p "$OUT"

# Notes on flags:
#   -p N          population size
#   -s SEED       reproducible
#   -m REGEX      only run modules whose name matches; keeps the record set
#                 small and dental-centric. Custom modules in ./modules are
#                 picked up via generate.local_modules_dir (see config).
#   --exporter.*  CSV on (what the ETL reads), FHIR off (not needed yet),
#                 years_of_history 5 so each patient has several recalls.
java -jar "$JAR" \
  -p "$N" \
  -s "$SEED" \
  -c "$HERE/config/synthea.properties" \
  -m "dental*|*_dental*|wellness_encounters" \
  --exporter.baseDirectory="$OUT" \
  --exporter.csv.export=true \
  --exporter.fhir.export=false \
  --exporter.years_of_history=5 \
  Massachusetts

echo
echo "Done. CSVs in $OUT/csv/"
ls -1 "$OUT/csv" | sed 's/^/  /'
