#!/bin/bash
set -e

# --------------------------------------------------------------
# GaseraMux: Switch Measurement Start Mode
# --------------------------------------------------------------
# Purpose:
#   Configure when the Gasera measurement starts for MOTOR tasks
#   via the local REST API (
#   /gasera/api/measurement/config).
#
# Quick usage:
#   - Run without arguments or with 'status' to see usage and
#     show the current configuration.
#   - Requires root (sudo).
# --------------------------------------------------------------

MODE="$1"
HOST="http://127.0.0.1"   # adjust if needed
ENDPOINT="$HOST/gasera/api/measurement/config"

usage() {
  echo
  echo "Usage:"
  echo "  sudo $0 {per_cycle|per_task|status}"
  echo
  echo "Description:"
  echo "  Configure when Gasera measurement is started for MOTOR tasks."
  echo
  echo "Modes:"
  echo "  per_cycle : Start/stop measurement for each motor cycle (default)"
  echo "  per_task  : Start measurement once per task, stop at task end"
  echo "  status    : Show current measurement_start_mode"
  echo
  echo "Notes:"
  echo "  - Changes affect future tasks only"
  echo "  - No service restart is required"
}

show_status() {
  echo
  echo "[GASERA] Current measurement configuration:"
  RESPONSE=$(curl -s "$ENDPOINT")
  if [[ -z "$RESPONSE" ]]; then
    echo "[ERROR] Empty response from $ENDPOINT"
    echo "         Check HOST/port configuration."
  else
    echo "$RESPONSE" | tee /tmp/gasera_cfg_status.json
  fi
  echo
}

# --------------------------------------------------------------
# Handle status / missing / invalid arguments
# --------------------------------------------------------------
if [[ -z "$MODE" || "$MODE" == "status" ]]; then
  usage
  show_status
  exit 0
fi

if [[ "$MODE" != "per_cycle" && "$MODE" != "per_task" ]]; then
  echo "[ERROR] Invalid argument: $MODE"
  usage
  show_status
  exit 1
fi

# --------------------------------------------------------------
# Require root for modifications
# --------------------------------------------------------------
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo $0)"
  usage
  exit 1
fi

# --------------------------------------------------------------
# Apply configuration
# --------------------------------------------------------------
echo "[GASERA] Setting measurement_start_mode to: $MODE"

HTTP_CODE=$(curl -s -o /tmp/gasera_cfg_resp.json -w "%{http_code}" \
  -X POST "$ENDPOINT" \
  -H "Content-Type: application/json" \
  -d "{\"measurement_start_mode\": \"$MODE\"}")

if [[ "$HTTP_CODE" != "200" ]]; then
  echo "[ERROR] Failed to update measurement configuration"
  cat /tmp/gasera_cfg_resp.json
  exit 1
fi

echo "[GASERA] Configuration updated successfully"

# --------------------------------------------------------------
# Verify
# --------------------------------------------------------------
show_status
echo "[GASERA] Done."
