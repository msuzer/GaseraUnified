import re
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

from system.log_utils import debug, info, warn, error

# Default paths and constants (kept at module level for clarity)
APP_DIR = Path("/opt/GaseraMux")
CONFIG_DIR = APP_DIR / "config"
INSTALL_DIR = APP_DIR / "install"
LAST_PATH = APP_DIR / "last_version.txt"
VERSION_INFO = APP_DIR / "version_info.sh"
API_SECRET_PATH = CONFIG_DIR / "api_secret"

SERVICE_NAME = "gasera.service"

SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


class VersionManager:
    """Encapsulates version control and service restart operations.

    Instantiate with optional paths for easier testing.
    """

    def __init__(self, app_dir: Path = APP_DIR, config_dir: Path = CONFIG_DIR, install_dir: Path = INSTALL_DIR):
        self.app_dir = Path(app_dir)
        self.config_dir = Path(config_dir)
        self.install_dir = Path(install_dir)
        self.last_path = self.app_dir / "last_version.txt"
        self.version_info = self.app_dir / "version_info.sh"
        self.api_secret = self.config_dir / "api_secret"

    def _run(self, cmd, **kw) -> str:
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=kw.pop("timeout", 60), **kw).stdout.strip()

    def read_version_info(self) -> Dict[str, str]:
        info_map: Dict[str, str] = {}
        if self.version_info.exists():
            for line in self.version_info.read_text().splitlines():
                if line.startswith("BUILD_"):
                    k, v = line.split("=", 1)
                    info_map[k] = v.strip().strip('"')
        return info_map

    def current_full_sha(self) -> str:
        try:
            return self._run(["git", "-C", str(self.app_dir), "rev-parse", "HEAD"])
        except Exception:
            vi = self.read_version_info()
            return vi.get("BUILD_HASH", "unknown")

    def _regen_version_info(self) -> None:
        gen = self.install_dir / "gen_version.sh"
        if gen.exists():
            self._run([str(gen)])
        else:
            now = time.strftime("%Y-%m-%d")
            short = "manual"
            branch = "unknown"
            if (self.app_dir / ".git").exists():
                try:
                    short = self._run(["git", "-C", str(self.app_dir), "rev-parse", "--short", "HEAD"])
                    branch = self._run(["git", "-C", str(self.app_dir), "rev-parse", "--abbrev-ref", "HEAD"])
                except Exception:
                    pass

            self.version_info.write_text(
                f'BUILD_HASH="{self.current_full_sha()}"\n'
                f'BUILD_SHORT="{short}"\n'
                f'BUILD_BRANCH="{branch}"\n'
                f'BUILD_DATE="{now}"\n'
                f'BUILD_DESCRIBE="manual"\n'
                f'BUILD_MESSAGE="manual write"\n'
            )

    def _normalize_perms_and_prefs(self) -> None:
        # mirror relevant parts of update.sh without resetting git
        self._run(["bash", "-lc", f'find {self.app_dir} -type f -name "*.sh" -exec chmod 755 {{}} \;' ])
        self._run(["bash", "-lc", f'find {self.app_dir} -type f ! -name "*.sh" -exec chmod 644 {{}} \;' ])
        self._run(["bash", "-lc", f'find {self.app_dir} -type d -exec chmod 755 {{}} \;' ])
        prefs = self.config_dir / "user_prefs.json"
        if prefs.exists():
            try:
                self._run(["chgrp", "www-data", str(prefs)])
                self._run(["chmod", "660", str(prefs)])
            except Exception:
                pass

    def _restart_service(self, reason: str = "") -> None:
        info(f"Restarting {SERVICE_NAME} {reason}".strip())
        try:
            from system import services
            services.buzzer.play("service_restart")
            services.display_controller.show(
                services.display_adapter.info("Version Manager:", "Restarting Service...")
            )
        except Exception as e:
            warn(f"[version_manager] UX feedback failed: {e}")

        proc = subprocess.run(["systemctl", "restart", SERVICE_NAME], capture_output=True, text=True)
        state = subprocess.run(["systemctl", "is-active", SERVICE_NAME], capture_output=True, text=True)
        if state.stdout.strip() != "active":
            msg = proc.stderr.strip() or "Service did not reach active state"
            error(f"Service restart problem: {msg}")
            raise RuntimeError(msg)
        info("Service restarted successfully")

    def require_admin(self, request) -> bool:
        if request.remote_addr in ("127.0.0.1", "::1"):
            return True
        token_hdr = request.headers.get("X-Admin-Token", "")
        if self.api_secret.exists() and token_hdr:
            secret = self.api_secret.read_text().strip()
            return bool(secret) and token_hdr == secret
        return False

    def _is_same_commit(self, target: str, current_full: str) -> bool:
        return current_full.startswith(target) if 7 <= len(target) <= 40 else False

    def checkout_commit(self, sha: str) -> Dict[str, Any]:
        if not SHA_RE.match(sha):
            raise ValueError("Invalid SHA")
        current = self.current_full_sha()
        if self._is_same_commit(sha, current):
            debug(f"noop checkout: already on {current[:7]}")
            return {"previous": current, "current": current, "noop": True}

        self.last_path.write_text(current + "\n")
        debug(f"checkout requested sha={sha} current={current}")
        self._run(["git", "-C", str(self.app_dir), "fetch", "--all", "--prune"])

        proc = subprocess.run(["git", "-C", str(self.app_dir), "checkout", "--detach", sha, "-f"], capture_output=True, text=True)
        if proc.returncode != 0:
            msg = proc.stderr.strip() or proc.stdout.strip() or "git checkout failed"
            error(f"git checkout returned {proc.returncode}: {msg}")
            raise RuntimeError(msg)
        else:
            debug(f"git checkout OK: {proc.stdout.strip()}")

        self._normalize_perms_and_prefs()
        self._regen_version_info()
        self._restart_service(f"after version checkout to {sha}")

        new_sha = self.current_full_sha()
        info(f"checkout completed sha={sha} now={new_sha}")
        return {"previous": current, "current": new_sha}

    def rollback_previous(self) -> Dict[str, str]:
        if not self.last_path.exists():
            raise RuntimeError("No previous version recorded")
        prev = self.last_path.read_text().strip()
        if not SHA_RE.match(prev):
            raise RuntimeError("Invalid previous SHA recorded")

        info(f"rollback requested to {prev}")
        self._run(["git", "-C", str(self.app_dir), "fetch", "--all", "--prune"])
        self._run(["git", "-C", str(self.app_dir), "checkout", "--detach", prev])
        self._normalize_perms_and_prefs()
        self._regen_version_info()
        self._restart_service("after version rollback")
        now = self.current_full_sha()
        info(f"rollback completed now={now}")
        return {"current": now}

# End of system/version_manager.py
