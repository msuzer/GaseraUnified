# Measurement Logger Architecture

This document explains how measurement data is logged, where it is stored (USB vs. local SD), how files are segmented and merged, and how partial segments are recovered on startup.

## Storage Locations

- Primary internal storage: `/data/logs`
- USB storage (preferred when present): `/media/usb0/logs`
- Temporary segments folder: `.tmp` under the active log root

The active log root is selected at runtime by `gasera/storage_utils.get_log_directory()`:
- If a USB block device is present and mounted at `/media/usb0`, logs go to `/media/usb0/logs`.
- Otherwise, logs go to `/data/logs`.

The USB mount detection uses a two-step check to avoid blocking on automount:
1) Detect `/dev/sdX1` presence
2) Verify `/media/usb0` is mounted

Related endpoints:
- `GET /gasera/api/logs/storage` — reports current active storage and free/total space

## File Structure

Logger implementation: [gasera/measurement_logger.py](../gasera/measurement_logger.py)

- Final CSV files:
  - Name: `gasera_log_<YYYYMMDD>_<HHMMSS>_<RUNID>.csv`
  - Wide format with one row per measurement result
- Segment TSV files:
  - Name: `segment_<RUNID>_<index>.tsv`
  - Stored under `.../.tmp/`
  - Flushed and fsync'ed after each write

### Columns

The header is built from the first measurement (component labels) and written once. Columns:
- `timestamp` (ISO-8601 or device-provided readable time)
- `phase` (padded for readability)
- `channel` (1-based on UI)
- `repeat` (cycle index)
- Component columns: one per label, values formatted to 4 decimal places

Duplicate entries are suppressed using timestamp deduplication (UNIX epoch or ISO parsing).

## Segmentation and Merging

- Segment duration: 3600 seconds (1 hour) per segment (`SEGMENT_SECONDS = 3600`).
- Each write checks segment age and rotates when the threshold is reached.
- On successful task completion (`MeasurementLogger.close(success=True)`):
  - All segments for the run are merged into the final CSV.
  - Segment files are cleaned up.
- On failure (`success=False`) or merge error:
  - Segments are preserved in `.tmp` for recovery.

## Recovery on Startup

The application runs `recover_incomplete_segments()` during startup (see [app.py](../app.py) and [system/log_recovery_service.py](../system/log_recovery_service.py)):
- Groups leftover `segment_<RUNID>_###.tsv` files by `RUNID`.
- Merges each group into a recovered CSV named `gasera_log_<YYYYMMDD>_<HHMMSS>_<RUNID>_RECOVERED.csv` in the active log root.
- Cleans up the recovered segments for that run.

## SD Card Longevity and Mount Options

For devices using SD storage, see [install/sd_life_tweaks.sh](../install/sd_life_tweaks.sh), which applies safer mount options and reduces write amplification:
- Root filesystem (ext4): `noatime,nodiratime,lazytime,commit=60,errors=remount-ro`
- Mount `/var/log`, `/tmp`, `/var/tmp` as `tmpfs` (RAM)
- Journald logs volatile (RAM-backed) with size caps
- Swap disabled (optional zram swap available)

These changes reduce frequent small writes and improve SD endurance. Logger still calls `fsync()` to ensure data is flushed to the current storage device.

## Listing and Downloading Logs

- List logs (paged): `GET /gasera/api/logs?page=1&page_size=50`
- List segments (unfinished runs): `GET /gasera/api/logs?segments=1`
- Download a specific file:
  - Completed CSV: `GET /gasera/api/logs/<filename.csv>`
  - Segment TSV: `GET /gasera/api/logs/<filename.tsv>?segments=1`
- Optional locale export for CSV download: `?locale=tr-TR` (decimal comma)

## Troubleshooting

- Check current storage: `GET /gasera/api/logs/storage`
- Verify USB mount and free space before starting a long run
- Review startup recovery messages in the service logs (journalctl)

