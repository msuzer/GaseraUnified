# Frontend User Manual (Beginner Guide)

Welcome to the Gasera Multiplexer Controller web interface. This guide explains how to use the dashboard to start measurements, view results, manage settings, and check device status — no prior experience required.

---

## Getting Started

- Open your web browser and visit the controller page provided by your administrator (often `http://<controller-ip>/`).
- The page loads three tabs: Home, Results, and Settings. You can switch tabs using the buttons near the top.
- The status bar at the bottom shows whether the Gasera device is online and the current activity.

---

## Home Tab

Purpose: Start, stop, and monitor measurements.

Main elements:
- **Start Measurement**: Begins a new measurement cycle. A short countdown allows canceling before it starts.
- **Abort**: Stops the current measurement immediately.
- **Repeat / Finish**: Available when the system is armed; repeat starts the next cycle, finish ends the session safely.
- **Channel Selection** (Mux mode): Pick which channels to include. You can select up to 31 channels.
- **Preferences**: Quick controls like duration, pause, repeat count, buzzer on/off.

During measurements:
- The Start button shows the current phase (e.g., Measuring, Switching) with the active channel and timing.
- Progress indicators show both the current step and overall progress.
- Notifications appear on completion or abort with a brief summary.

Tips:
- If the system is waiting for a trigger, the Start button says "Waiting for Trigger".
- You can toggle buzzer feedback from Home. Other clients will see the change.

---

## Results Tab

Purpose: View live charts during measurement or play back saved CSVs.

Features:
- **Live Mode**: Plots gas components in real time. The top-right notice shows "Live Mode".
- **Playback Mode (CSV)**: Load a CSV to review past data. The notice shows the file name when active.
- **Legend Toggles**: Click entries in the legend or use the component switches to show/hide lines.
- **Zoom/Pan**: Use mouse wheel to zoom the time axis; drag to pan.
- **Download**:
  - Download **image** of the chart as PNG.
  - Download **CSV** in selected locale format.

Metadata in tooltips:
- Hover lines to see the **timestamp**, **component**, **ppm**, and (when available) **phase**, **channel**, **repeat**.

Notes:
- If a measurement is running, the app prevents switching to CSV playback.
- Track visibility changes are saved to preferences so your selections persist.

---

## Settings Tab

Purpose: Manage Wi-Fi, simulator mode, and device/service actions.

Wi-Fi:
- **Scan**: Lists nearby networks with signal strength indicators.
- **Connect**: Join a secured network (you’ll be prompted for a password) or open network.
- **Switch**: Move to a saved network.
- **Forget**: Remove a saved network.
- The header shows current connection details.

Simulator and Power Controls:
- **Simulator**: Toggle the built-in simulator for testing (if available).
- **Restart Service**: Restart the Gasera app service.
- **Restart / Shutdown Device**: Reboot or power off the controller hardware.

Motor Controls (if present):
- **Motor Jog**: Manually move the motor/actuator.
- **Timeout**: Adjust motor timeout if the profile is set to Motor.

---

## Status Bar

The footer shows connection and activity:
- **Wifi icon**: Online (solid) vs Offline (crossed out).
- **Label**: "Gasera Online" plus the current status (e.g., Measuring / Switching).
- **Timer**: When measuring, shows elapsed and total time (ET/TT).

If the server connection drops, a red banner appears at the top. Refresh the page after the connection is restored.

---

## Common Workflow

1. Open the **Home** tab.
2. Select your **channels** (Mux mode) and adjust **preferences** (duration, pause, repeats).
3. Click **Start Measurement**; the countdown allows canceling.
4. Watch progress; use **Abort** if needed.
5. When done, view data in **Results**. Download the chart or CSV.
6. Use **Settings** to adjust Wi-Fi or restart the service if the app stops responding.

---

## Troubleshooting

- **Gasera Offline**: Check cables and power. Ensure the controller and Gasera device are on the same network. If the problem persists, contact your administrator.
- **No Live Data**: Make sure a measurement is running. If not, start one from Home.
- **Cannot Load CSV**: End any active measurement first, then try again.
- **Connection or Network Issues**: Refresh the page. If you still have issues, contact your administrator.
- **Frozen UI**: Refresh the page. If it remains unresponsive, contact your administrator.

---

## Glossary

- **Mux Mode**: Multiplexer hardware controlling multiple gas channels.
- **Motor Mode**: Motor/actuator hardware profile.
- **Phase**: Measurement step, such as Homing, Switching, Paused, Measuring.
- **ET/TT**: Elapsed Time / Total Time.
- **SSE**: Server-Sent Events; live updates from the server.

---

## Tips for New Users

- Start simple: select a few channels, short duration, and one repeat.
- Use the legend toggles to focus on specific components.
- Keep the window open during measurements to see live updates.
- Learn the icons: wifi (online/offline) and stopwatch (timing indicator).

---

If you need help, contact your administrator or consult the main README for system-level documentation.