#!/usr/bin/env bash
set -euo pipefail

BASE_URL="https://gis.fdot.gov/arcgis/rest/services/Crashes_All/FeatureServer/0/query"

for n in $(seq 11 50); do
  upper=$((n * 1000))
  lower=$((upper - 1000))
  out="crash${upper}.json"

  if [ -f "$out" ]; then
    echo "Skipping $out (already exists)"
    continue
  fi

  echo "Fetching $out (OBJECTID >= ${lower})..."
  curl -fsS --get "$BASE_URL" \
    --data-urlencode "where=OBJECTID>=${lower}" \
    --data-urlencode "outFields=*" \
    --data-urlencode "f=geojson" \
    -o "$out"
done

echo "Done."
