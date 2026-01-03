import os, csv, uuid, time, shutil
from datetime import datetime
from typing import List

from system.log_utils import debug, info, warn


class MeasurementLogger:
    """
    Robust wide-format CSV logger with time-based segmentation.

    - Header is built automatically from the FIRST measurement.
    - Data is written into hourly segment files under .tmp/.
    - Files are flushed+fsync'ed regularly.
    - At successful task end, segments are merged into one CSV.
    """

    SEGMENT_SECONDS = 3600  # 1 hour

    def __init__(self, base_dir="/data/logs"):
        os.makedirs(base_dir, exist_ok=True)

        self.base_dir = base_dir
        self.run_id = uuid.uuid4().hex[:6].upper()

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.task_name = f"gasera_log_{ts}_{self.run_id}"
        self.final_path = os.path.join(base_dir, f"{self.task_name}.csv")

        self.tmp_dir = os.path.join(base_dir, ".tmp")
        os.makedirs(self.tmp_dir, exist_ok=True)

        debug(f"[LOGGER] temp log dir: {self.tmp_dir}")

        # segmentation state
        self.segment_index = 0
        self.segment_start_ts = 0.0
        self.f = None
        self.writer = None

        # header / schema state
        self.header_written = False
        self.component_headers: List[str] = []

        # duplicate detection
        self._last_logged_timestamp = None

        self._open_new_segment()

    # ------------------------------------------------------------
    # Segment handling
    # ------------------------------------------------------------
    def _segment_path(self) -> str:
        return os.path.join(
            self.tmp_dir,
            f"segment_{self.run_id}_{self.segment_index:03d}.tsv"
        )

    def _open_new_segment(self):
        self.segment_start_ts = time.monotonic()
        path = self._segment_path()

        debug(f"[LOGGER] opening segment: {path}")

        self.f = open(path, "w", newline="")
        self.writer = csv.writer(self.f, delimiter="\t")

        # header only goes into the FIRST segment
        if self.segment_index == 0 and self.header_written:
            header = ["timestamp", "phase", "channel", "repeat"] + self.component_headers
            self.writer.writerow(header)
            self.f.flush()
            os.fsync(self.f.fileno())

        self.segment_index += 1

    def _close_segment(self):
        if not self.f:
            return

        try:
            self.f.flush()
            os.fsync(self.f.fileno())
        except Exception as e:
            warn(f"[LOGGER] flush failed: {e}")

        try:
            self.f.close()
        except Exception:
            pass

        self.f = None
        self.writer = None

    def _cleanup_segments(self):
        try:
            for name in os.listdir(self.tmp_dir):
                if name.startswith(f"segment_{self.run_id}_"):
                    path = os.path.join(self.tmp_dir, name)
                    if os.path.isfile(path):
                        os.remove(path)
            debug(f"[LOGGER] cleaned up segment files in {self.tmp_dir}")
        except Exception as e:
            warn(f"[LOGGER] cleanup failed: {e}")

    # ------------------------------------------------------------
    # Header logic (from old logger)
    # ------------------------------------------------------------
    def _write_header_if_needed(self, components):
        if self.header_written:
            return

        if not components:
            warn("[LOGGER] No components found to build CSV header")
            return

        self.component_headers = [c["label"] for c in components]
        self.header_written = True

        # If first segment already open, write header immediately
        if self.segment_index == 1 and self.writer:
            header = ["timestamp", "phase", "channel", "repeat"] + self.component_headers
            self.writer.writerow(header)
            self.f.flush()
            os.fsync(self.f.fileno())

        debug(f"[LOGGER] CSV header written: {self.component_headers}")

    # ------------------------------------------------------------
    # PUBLIC API — write one measurement
    # ------------------------------------------------------------
    def write_measurement(self, live: dict) -> bool:
        if not live:
            return False

        if self._is_duplicate_live_result(live):
            return False

        # rotate segment if needed
        if time.monotonic() - self.segment_start_ts >= self.SEGMENT_SECONDS:
            self._close_segment()
            self._open_new_segment()

        ts = live.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        comps = live.get("components", [])
        if not comps:
            return False

        self._write_header_if_needed(comps)
        if not self.header_written:
            return False

        phase_text = str(live.get("phase", ""))
        phase_padded = phase_text.ljust(10)

        row = [
            ts,
            phase_padded,
            live.get("channel"),
            live.get("repeat"),
        ]

        def _fmt_ppm(v):
            try:
                return f"{float(v):.4f}"
            except Exception:
                return ""

        values_by_label = {
            c.get("label"): _fmt_ppm(c.get("ppm"))
            for c in comps
            if c and c.get("label") is not None
        }

        for label in self.component_headers:
            row.append(values_by_label.get(label, ""))

        try:
            self.writer.writerow(row)
            self.f.flush()
            os.fsync(self.f.fileno())
            return True
        except Exception as e:
            warn(f"[LOGGER] write failed: {e}")
            self._close_segment()
            self._open_new_segment()
            return False

    # ------------------------------------------------------------
    # Finalization
    # ------------------------------------------------------------
    def close(self, success: bool = True):
        self._close_segment()

        if not success:
            warn("[LOGGER] task failed, keeping segment files")
            return

        try:
            self._merge_segments()
        except Exception as e:
            warn(f"[LOGGER] merge failed: {e}")
            warn("[LOGGER] segment files kept")
            return
            
        # merge successful → cleanup
        self._cleanup_segments()

    def _merge_segments(self):
        segments = sorted(
            f for f in os.listdir(self.tmp_dir)
            if f.startswith(f"segment_{self.run_id}_") and f.endswith(".tsv")
        )

        if not segments:
            warn("[LOGGER] no segments to merge")
            return

        debug(f"[LOGGER] merging {len(segments)} segments → {self.final_path}")

        with open(self.final_path, "w", newline="") as out:
            for name in segments:
                path = os.path.join(self.tmp_dir, name)
                with open(path, "r") as src:
                    shutil.copyfileobj(src, out)

        debug("[LOGGER] merge successful")

    # ------------------------------------------------------------
    # Duplicate detection (unchanged)
    # ------------------------------------------------------------
    def _extract_timestamp(self, result):
        ts = result.get("timestamp")

        if isinstance(ts, (int, float)):
            return float(ts)

        if isinstance(ts, str):
            try:
                iso = ts.replace(" ", "T")
                return datetime.fromisoformat(iso).timestamp()
            except Exception:
                try:
                    return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").timestamp()
                except Exception:
                    return None

        return None

    def _is_duplicate_live_result(self, result):
        ts = self._extract_timestamp(result)
        if ts is None:
            return True

        if self._last_logged_timestamp == ts:
            return True

        self._last_logged_timestamp = ts
        return False
