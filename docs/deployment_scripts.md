# Deployment Scripts Guide

This document outlines the deploy, update, and uninstall scripts under `install/`, what they do, and how to use them. It also notes minor inconsistencies observed and how they were addressed.

For details of the installed systemd/Nginx configs, udev rules, preferences template, and USB setup, see [system configurations](system_configs.md).

## deploy.sh

Path: install/deploy.sh

Purpose: Provision the Orange Pi Zero 3 for GaseraMux. Installs packages, clones the repo, sets permissions, configures services (systemd, Nginx), sets up DHCP on `end0`, and applies optional SD-card longevity tweaks.

Key steps:
- Packages: `isc-dhcp-server`, `nginx`, `python3`, Flask/Waitress, GPIO/I2C libs, NetworkManager, etc.
- Device profile: interactively set to `MUX` or `MOTOR` and write `system/device/device_profile.py`.
- Repo: clone/pull from GitHub into `/opt/GaseraMux` (branch argument optional).
- Permissions: normalize ownerships and modes across files and directories.
- Udev: install `install/99-gpio.rules`; add `www-data` to `gpio`, `i2c`, `dialout`.
- Logs: ensure internal `/data/logs` and USB `/media/usb0/logs` exist and are writable.
- Services: install `install/gasera.service`, enable and restart; install Nginx site `install/gasera.conf`.
- Network: create/modify `gasera-dhcp` connection on `end0` with static `192.168.0.1/24`; configure ISC DHCP with a reserved IP (`192.168.0.100`) for a specified MAC.
- Version info: run `install/gen_version.sh`.
- Post-deploy: optional cleanup via `install/sd_clean.sh`, optional SD tweaks via `install/sd_life_tweaks.sh`, optional simulator service via `sim/install_simulator.sh`.

Usage:
```bash
cd /opt
sudo git clone https://github.com/msuzer/GaseraMux.git
cd GaseraMux/install
sudo ./deploy.sh              # interactive
sudo ./deploy.sh <branch>     # deploy specific branch
```

Notes:
- Requires root (sudo).
- Network interface is `end0` by default; adjust `IFACE` at script top if needed.
- DHCP server is bound to `end0` and waits for the static IP before starting.

## update.sh

Path: install/update.sh

Purpose: Synchronize `/opt/GaseraMux` with remote branch, preserve user preferences and device profile, normalize permissions, regenerate version info, and restart the service.

Key steps:
- Branch selection: argument or current branch fallback; defaults to `main` when repo absent.
- Preserves device profile from `system/device/device_profile.py` and reapplies after checkout.
- Git operations: reset/clean, fetch all, checkout branch to match `origin`, hard reset.
- Permissions: directories `755`, files `644` (excluding `config/user_prefs.json`), marks scripts executable.
- Logs directory permissions: internal `/data/logs`, USB `/media/usb0/logs`.
- Version info: run `install/gen_version.sh`.
- Service: restart `gasera.service`.

Usage:
```bash
cd /opt/GaseraMux/install
sudo ./update.sh            # update current branch
sudo ./update.sh <branch>   # switch/update to specific branch
```

Note:
- Requires root (sudo).
- Minor inconsistency fixed: path for `device_profile.py` corrected to `system/device/device_profile.py` during preservation.

## uninstall.sh

Path: install/uninstall.sh

Purpose: Soft uninstall. Stops and disables `gasera.service`, removes `/opt/GaseraMux`, cleans Nginx site and the app’s NetworkManager connection/DHCP override, and preserves udev rules and backups.

Key steps:
- Stop/disable systemd service; remove unit file.
- Remove application directory and clean `git safe.directory` setting.
- Remove Nginx site (`gasera.conf`) and reload.
- Network cleanup: delete `gasera-dhcp` connection; disable `isc-dhcp-server` and remove service override; truncate leases.
- Clean logs/cache; preserve GPIO/I2C udev rules and deploy backups.
- Write manifest to `/root/gasera_cleanup_manifest_YYYY-MM-DD_HHMMSS.txt`.

Usage:
```bash
cd /opt/GaseraMux/install
sudo ./uninstall.sh
```

Notes:
- Requires root (sudo).
- Leaves base DHCP configs intact but disables the service. Re-deploy to enable again.

## Cross-script Consistency

- Device profile persistence: `deploy.sh` sets profile; `update.sh` preserves and reapplies it; `uninstall.sh` does not touch profile files after directory removal.
- Log directories: all scripts ensure `/data/logs` and `/media/usb0/logs` exist and have proper permissions.
- Services: `deploy.sh` installs/enables `gasera.service`; `update.sh` restarts; `uninstall.sh` disables and removes.
- Network: `deploy.sh` creates `gasera-dhcp` on `end0` + ISC DHCP override; `uninstall.sh` removes both. Verified consistent.

## Troubleshooting

- Service status:
```bash
sudo systemctl status gasera.service
sudo journalctl -u gasera.service -e
```
- DHCP:
```bash
sudo systemctl status isc-dhcp-server
sudo journalctl -u isc-dhcp-server -f
cat /var/lib/dhcp/dhcpd.leases
```
- Nginx:
```bash
sudo nginx -t
sudo systemctl restart nginx
```

