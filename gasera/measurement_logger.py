# gasera/measurement_logger.py
import os
import csv
import uuid
from datetime import datetime
from system.log_utils import debug, info, warn

class MeasurementLogger:
    """
    Wide-format CSV logger.

    Header is created from the FIRST measurement's component list.
    Subsequent rows stick to that exact structure. Components = list of
    objects from SSE/live:
        { "label": "...", "ppm": value, "color": "...", "cas": "..." }
    """

    def __init__(self, base_dir="/data/logs"):
        os.makedirs(base_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = uuid.uuid4().hex[:6].upper()
        self.filename = os.path.join(base_dir, f"gasera_log_{ts}_{suffix}.csv")

        info(f"MeasurementLogger (wide): logging to {self.filename}")

        # open file for writing; use tab delimiter to avoid conflict with decimal comma
        self.f = open(self.filename, "w", newline="")
        self.writer = csv.writer(self.f, delimiter='\t')

        self.header_written = False
        self.component_headers = []    # populated after first measurement
        self._last_logged_timestamp = None

    # ------------------------------------------------------------
    # INTERNAL — Write header when we see the first measurement
    # ------------------------------------------------------------
    def _write_header_if_needed(self, components):
        """
        components is a list of dicts (from ACON/SSE):
            [
                { "label": "...", "ppm": x, "color": "...", "cas": "..." },
                ...
            ]
        """
        if self.header_written:
            return

        if not components:
            warn("[LOGGER] No components found to build CSV header")
            return

        # Grab the labels in device order
        self.component_headers = [c["label"] for c in components]

        header = ["timestamp", "phase", "channel", "repeat"] + self.component_headers
        self.writer.writerow(header)
        self.f.flush()

        self.header_written = True
        debug(f"[LOGGER] CSV header written: {header}")

    # ------------------------------------------------------------
    # PUBLIC — Write one measurement in wide format
    # ------------------------------------------------------------
    def write_measurement(self, live: dict) -> bool:
        """
        live:
        {
            "timestamp": "...",
            "phase": ...,
            "channel": ...,
            "repeat": ...,
            "components": [
                { "label": "...", "ppm": x, "color": "...", "cas": "..." },
                ...
            ]
        }
        """
        if not live:
            return False
        
        if self._is_duplicate_live_result(live):
            return False

        # Timestamp: prefer live.timestamp, fallback to now
        ts = live.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        comps = live.get("components", [])

        if not comps:
            return False

        # Ensure header exists
        self._write_header_if_needed(comps)
        if not self.header_written:
            return False  # header still missing → skip

        # Build the row
        # Phase/channel/repeat: prefer live, fallback to progress snapshot
        phase_text = str(live.get("phase", ""))
        # Pad phase for consistent visual alignment when viewing TSV in plain text
        phase_padded = phase_text.ljust(10)
        row = [
            ts,
            phase_padded,                # padded to fixed width for readability
            live.get("channel"),
            live.get("repeat"),
        ]

        # Add gas values in the header-defined order
        # Normalize ppm and format consistently to fixed precision (improves visual alignment)
        def _fmt_ppm(v):
            try:
                return f"{float(v):.4f}"
            except Exception:
                return ""

        values_by_label = {c.get("label"): _fmt_ppm(c.get("ppm")) for c in comps if c and c.get("label") is not None}

        for label in self.component_headers:
            row.append(values_by_label.get(label, ""))

        debug(f"[LOGGER] Writing CSV row: {row}")

        self.writer.writerow(row)
        self.f.flush()
        
        return True

    # ------------------------------------------------------------
    def close(self):
        try:
            self.f.close()
            self.f = None
            self.writer = None
        except Exception as e:
            warn(f"[LOGGER] Error closing CSV file: {e}")

    # ------------------------------------------------------------
    # Private methods for duplicate detection
    # ------------------------------------------------------------
    def _extract_timestamp(self, result):
        """
        Extracts timestamp for duplicate detection.

        Gasera ACON timestamps are in UNIX epoch seconds (int/float).
        Some older firmware versions may return a string ("readable")
        timestamp. This function supports both.

        Returns:
            float epoch timestamp, or None if invalid.
        """
        if not result:
            warn("[ENGINE] Missing result object in timestamp extractor")
            return None

        ts = result.get("timestamp")

        # ------------------------------------------------------------
        # 1. UNIX epoch (Gasera primary format)
        # ------------------------------------------------------------
        if isinstance(ts, (int, float)):
            debug(f"[ENGINE] Timestamp detected as UNIX epoch: {ts}")
            return float(ts)
        # ------------------------------------------------------------
        # 2. Legacy readable timestamps (string)
        # ------------------------------------------------------------
        if isinstance(ts, str):
            s = ts.strip()

            # ISO 8601: "YYYY-MM-DDTHH:MM:SS"
            try:
                iso = s.replace(" ", "T")  # allow "YYYY-MM-DD HH..."
                dt = datetime.fromisoformat(iso)
                debug(f"[ENGINE] Timestamp parsed as ISO: {ts}")
                return dt.timestamp()
            except Exception:
                pass
            # Common format: "YYYY-MM-DD HH:MM:SS"
            try:
                dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
                debug(f"[ENGINE] Timestamp parsed as YYYY-MM-DD HH:MM:SS: {ts}")
                return dt.timestamp()
            except Exception:
                pass

            warn(f"[ENGINE] Unrecognized string timestamp format: {ts!r}")
            return None

        # ------------------------------------------------------------
        # 3. Invalid timestamp type
        # ------------------------------------------------------------
        if ts is not None:
            warn(f"[ENGINE] Invalid timestamp type {type(ts).__name__}: {ts!r}")

        return None

    def _is_duplicate_live_result(self, result):
        ts = self._extract_timestamp(result)
        if ts is None:
            return True  # ignore invalid values

        if self._last_logged_timestamp == ts:
            return True  # duplicate

        # update state
        self._last_logged_timestamp = ts
        return False
