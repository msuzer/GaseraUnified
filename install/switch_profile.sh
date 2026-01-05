#!/bin/bash
set -e

# --------------------------------------------------------------
# GaseraMux: Switch Device Profile
# --------------------------------------------------------------
# Purpose:
#   Switch the acquisition device profile used by the service
#   between pneumatic MUX and MOTOR actuator modes.
#
# Quick usage:
#   - Run without arguments or with 'status' to see usage and
#     show the current profile.
#   - Requires root; restarts 'gasera' systemd service on change.
# --------------------------------------------------------------

PROFILE="$1"
FILE="/opt/GaseraMux/system/device/device_profile.py"

usage() {
    echo
    echo "Usage:"
    echo "  sudo $0 {mux|motor|status}"
    echo
    echo "Description:"
    echo "  Switch the acquisition device profile used by the service."
    echo
    echo "Profiles:"
    echo "  mux    : Pneumatic multiplexer control"
    echo "  motor  : Dual motor actuator control"
    echo "  status : Show current profile"
    echo
    echo "Notes:"
    echo "  - Requires root (sudo)"
    echo "  - Restarts 'gasera' systemd service"
}

show_status() {
    echo
    echo "[GASERA] Current device profile:"
    if [[ -f "$FILE" ]]; then
        if grep -q "Device.MUX" "$FILE"; then
            echo '{"profile":"mux"}' | tee /tmp/gasera_profile_status.json
        elif grep -q "Device.MOTOR" "$FILE"; then
            echo '{"profile":"motor"}' | tee /tmp/gasera_profile_status.json
        else
            echo '{"profile":"unknown"}' | tee /tmp/gasera_profile_status.json
        fi
    else
        echo "[ERROR] Profile file not found: $FILE"
    fi
    echo
}

# --------------------------------------------------------------
# Validate input (non-root allowed for status)
# --------------------------------------------------------------
if [[ -z "$PROFILE" || "$PROFILE" == "status" ]]; then
    usage
    show_status
    exit 0
fi

if [[ "$PROFILE" != "mux" && "$PROFILE" != "motor" ]]; then
    echo "[ERROR] Invalid argument: $PROFILE"
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

echo "[GASERA] Switching profile to: $PROFILE"

# --------------------------------------------------------------
# Update device_profile.py
# --------------------------------------------------------------
if [[ "$PROFILE" == "mux" ]]; then
    sed -i 's/^DEVICE = Device\..*/DEVICE = Device.MUX/' $FILE
else
    sed -i 's/^DEVICE = Device\..*/DEVICE = Device.MOTOR/' $FILE
fi

# --------------------------------------------------------------
# Restart gasera service
# --------------------------------------------------------------
systemctl restart gasera
echo "[GASERA] gasera restarted with profile: $PROFILE"