#!/usr/bin/with-contenv bashio
set -e

PORT="$(bashio::config 'port')"
OUTPUT="$(bashio::config 'output')"
REPORT_EVERY="$(bashio::config 'report_every')"
STALL_TIMEOUT="$(bashio::config 'stall_timeout')"

mkdir -p "$(dirname "${OUTPUT}")"

bashio::log.info "Opnemen op UDP-poort ${PORT} naar ${OUTPUT}"

# --quiet: een regel per pakket is 17.000 logregels per dag. De periodieke
# inventaris vertelt je hetzelfde in één blok.
exec python3 /opt/moma/moma_record.py listen \
  --port "${PORT}" \
  --out "${OUTPUT}" \
  --report-every "${REPORT_EVERY}" \
  --stall-timeout "${STALL_TIMEOUT}" \
  --quiet
