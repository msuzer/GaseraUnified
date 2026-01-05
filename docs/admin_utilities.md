# Admin Utilities

Brief guide to the maintenance utilities included under `install/`.

## Device Profile Switch

Script: install/switch_profile.sh

- Purpose: Switch acquisition profile between pneumatic MUX and MOTOR.
- Usage:
  - Show status: `./install/switch_profile.sh status` (no sudo required)
  - Set MUX: `sudo ./install/switch_profile.sh mux`
  - Set MOTOR: `sudo ./install/switch_profile.sh motor`
- Notes:
  - Requires root when changing the profile.
  - Restarts `gasera` systemd service on change.

## Measurement Start Mode (Motor)

Script: install/switch_measurement_mode.sh

- Purpose: Configure when Gasera measurement starts for MOTOR tasks via REST.
- Endpoint: `/gasera/api/measurement/config`
- Modes:
  - `per_cycle`: Start/stop measurement for each motor cycle.
  - `per_task`: Start once per task, stop at task end.
- Usage:
  - Show status: `./install/switch_measurement_mode.sh status` (no sudo required)
  - Set per_cycle: `sudo ./install/switch_measurement_mode.sh per_cycle`
  - Set per_task: `sudo ./install/switch_measurement_mode.sh per_task`
- Notes:
  - Changes affect future tasks; no service restart required.

## Tips

- Run scripts from the repository root so paths resolve correctly.
- If the API host/port differs, edit `HOST` inside `switch_measurement_mode.sh`.
- For troubleshooting, check journal logs:
  - `sudo journalctl -u gasera -n 100`