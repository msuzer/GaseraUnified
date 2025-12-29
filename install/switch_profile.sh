#!/bin/bash
set -e

PROFILE="$1"
FILE="/opt/GaseraMux/system/device/device_profile.py"

# --------------------------------------------------------------
# Require root
# --------------------------------------------------------------
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo $0)"
  exit 1
fi

# --------------------------------------------------------------
# Validate input
# --------------------------------------------------------------
if [[ "$PROFILE" != "mux" && "$PROFILE" != "motor" ]]; then
    echo "Usage: $0 {mux|motor}"
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