import os, re, shutil
from datetime import datetime
from collections import defaultdict

from gasera.storage_utils import get_log_directory
from system.log_utils import debug, warn, info


SEGMENT_RE = re.compile(r"^segment_([A-Fa-f0-9]{6})_(\d{3})\.tsv$")


def recover_incomplete_segments():
    base_dir = get_log_directory()
    tmp_dir = get_log_directory(temp_dir=True)

    groups = defaultdict(list)

    # 1) collect & group by run_id
    for name in os.listdir(tmp_dir):
        m = SEGMENT_RE.match(name)
        if not m:
            continue

        run_id, idx = m.group(1), int(m.group(2))
        groups[run_id].append((idx, name))

    if not groups:
        debug("[LOGGER] no incomplete segments found to recover")
        return

    info(f"[LOGGER] found {len(groups)} incomplete run(s) to recover")

    # 2) recover each run separately
    for run_id, items in groups.items():
        items.sort(key=lambda x: x[0])  # order by segment index

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = os.path.join(
            base_dir,
            f"gasera_log_{ts}_{run_id}_RECOVERED.csv"
        )

        warn(
            f"[LOGGER] recovering {len(items)} segments "
            f"for run {run_id} → {os.path.basename(target)}"
        )

        try:
            with open(target, "w", newline="") as out:
                for _, name in items:
                    path = os.path.join(tmp_dir, name)
                    with open(path, "r") as src:
                        shutil.copyfileobj(src, out)

        except Exception as e:
            warn(f"[LOGGER] failed to recover run {run_id}: {e}")
            warn("[LOGGER] leaving segment files intact")
            continue

        info(f"[LOGGER] successfully recovered run {run_id} to {target}")
        info(f"[LOGGER] cleaning up segment files for run {run_id}")

        # 3) cleanup only this run's segments
        for _, name in items:
            try:
                os.remove(os.path.join(tmp_dir, name))
            except Exception as e:
                warn(f"[LOGGER] failed to remove segment file {name}: {e}")
                pass

        info(f"[LOGGER] recovery complete for run {run_id}")
