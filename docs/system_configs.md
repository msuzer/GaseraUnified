# System Configuration Overview

This document consolidates the runtime system pieces that support the Gasera Unified Controller: systemd service, Nginx reverse proxy, udev rules, user preferences template, and the USB formatting/auto-mount helper.

These are installed and configured by install/deploy.sh. Use this as a reference for validation and troubleshooting.

---

## systemd Service (install/gasera.service)

Purpose: Runs the Flask app (via run.py) under systemd with sane security defaults.

Key settings:
- Unit: After=network.target; ensures service starts when networking is ready.
- Identity: User=www-data, Group=www-data.
- WorkingDirectory: /opt/GaseraMux.
- ExecStart: /usr/bin/python3 run.py (launches the app from WorkingDirectory).
- Restart: on-failure; auto-restarts on crash.
- UMask=0022: new files default to 644/755.
- NoNewPrivileges=no: allows escalations within process if required.
- PrivateTmp=yes: isolated /tmp for the service.
- ProtectSystem=full: mounts system directories read-only for the service.
- ProtectHome=yes: hides /home from the service.
- ReadWritePaths: /opt/GaseraMux/config, /var/log, /tmp writable.
- Install: WantedBy=multi-user.target (enabled at boot).

Notes:
- WorkingDirectory must exist and contain run.py.
- If the app writes outside of listed paths, expand ReadWritePaths accordingly.
- Use journalctl -u gasera.service to inspect logs.

---

## Nginx Reverse Proxy (install/gasera.conf)

Purpose: Fronts the Flask app, serves static assets, and properly proxies Server-Sent Events (SSE).

Key locations:
- server: listen 80 default_server; root /opt/GaseraMux; index index.html.
- /gasera/: reverse proxy to http://127.0.0.1:5001 with SSE options:
  - proxy_buffering off, proxy_cache off.
  - proxy_http_version 1.1; Connection "".
  - proxy_read_timeout 3600s; proxy_send_timeout 3600s.
- /static/: alias /opt/GaseraMux/static/; disables caching via headers.
- /: fallback proxy to http://127.0.0.1:5001 (non-prefixed app routes).

Notes:
- Ensure the backend listens on port 5001 (see run.py / waitress settings).
- SSE requires buffering disabled to stream events.
- Static assets live under /opt/GaseraMux/static.

---

## Udev Rules (install/99-gpio.rules)

Purpose: Grants device access to service user groups for GPIO, I²C, and USB serial.

Rules:
- GPIO: SUBSYSTEM=="gpio", KERNEL=="gpiochip*", GROUP="gpio", MODE="0660".
- I²C: SUBSYSTEM=="i2c", KERNEL=="i2c-[0-9]*", GROUP="i2c", MODE="0660".
- USB serial: SUBSYSTEM=="tty", KERNEL=="ttyUSB*", GROUP="dialout", MODE="0660".

Notes:
- Add www-data to groups: gpio, i2c, dialout for access.
- Reload rules with: sudo udevadm control --reload-rules && sudo udevadm trigger.

---

## Preferences Template (install/user_prefs.template)

Purpose: Seed configuration for system/preferences.py; copied to working config on first run or deploy.

Fields:
- measurement_duration: seconds (int).
- pause_seconds: seconds (int).
- motor_timeout: seconds (int).
- repeat_count: number of repeat cycles.
- buzzer_enabled: boolean.
- simulator_enabled: boolean.
- online_mode_enabled: boolean (save-on-device vs online semantics).
- measurement_start_mode: "per_cycle" or "per_task".
- include_channels: 31-length array of 0/1 flags.
- track_visibility: map of component display defaults on charts.

Notes:
- API: /system/preferences (GET/POST) manages runtime preferences.
- Template uses Unicode subscripts for chemical names; preserved as JSON strings.

---

## USB Format & Auto-mount (install/format_usb.sh)

Purpose: Interactive helper to wipe, partition, format, and auto-mount a USB drive to /media/usb0 with safe /etc/fstab settings.

Flow:
- Shows available devices and confirms destructive action.
- Unmounts existing partition if present.
- Wipes signatures and creates GPT with single ext4 partition.
- Formats partition with label GASERADRIVE.
- Creates mount point /media/usb0 and a logs directory.
- Sets ownership to www-data and permissions 775 for logs.
- Adds fstab entry: sync,noatime,nofail,x-systemd.automount.
- Tests mount via mount -a.

Usage:
- Default device: /dev/sda. Override with first arg.
  - Example: sudo ./format_usb.sh /dev/sdb

Fstab entry:
- LABEL=GASERADRIVE   /media/usb0   ext4   sync,noatime,nofail,x-systemd.automount   0   0

Notes:
- nofail prevents boot failure if the drive is missing.
- x-systemd.automount defers mounting until accessed, speeding boot.
- Logs folder path is used by the measurement logger when USB is available.

---

## Operational Tips

- After deploy, enable and start the service:
  - sudo systemctl enable gasera.service
  - sudo systemctl restart gasera.service
- Verify Nginx:
  - sudo nginx -t && sudo systemctl reload nginx
- Group membership:
  - sudo usermod -aG gpio,i2c,dialout www-data
- Preferences:
  - Use the web UI or POST to /system/preferences to update.
