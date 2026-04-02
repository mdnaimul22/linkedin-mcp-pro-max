"""Session manager — manages browser profiles, session state, and runtime identity.

Dependency Rule:
  imports FROM: standard library, config, schema, helpers(global)
  MUST NOT import: api, browser, providers, services, tools
"""

import json
import logging
import platform
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from config.settings import Settings
from helpers import secure_write_text, utcnow_iso
from schema.session import RuntimeState, SourceState

logger = logging.getLogger("linkedin-mcp.session")


class SessionManager:
    """Manages LinkedIn browser sessions, authentication artifacts, and runtime identity."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._runtime_id = self._generate_runtime_id()

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def runtime_id(self) -> str:
        """Unique identifier for this execution environment (OS + arch + container)."""
        return self._runtime_id

    # ------------------------------------------------------------------
    # Path resolution
    # ------------------------------------------------------------------

    @property
    def auth_root(self) -> Path:
        """Root directory for all auth-related files."""
        return self.settings.user_data_dir.parent

    @property
    def source_profile_dir(self) -> Path:
        """Primary browser profile directory (where the user logs in)."""
        return self.settings.user_data_dir

    @property
    def source_state_path(self) -> Path:
        """Metadata file path for the primary authenticated profile."""
        return self.auth_root / "source-state.json"

    @property
    def portable_cookies_path(self) -> Path:
        """Portable cookies file (used for multi-environment bridging)."""
        return self.auth_root / "cookies.json"

    @property
    def runtimes_root(self) -> Path:
        """Root directory for all derived runtime profiles."""
        return self.auth_root / "runtimes"

    def get_runtime_dir(self, runtime_id: str) -> Path:
        return self.runtimes_root / runtime_id

    def get_runtime_profile_dir(self, runtime_id: str) -> Path:
        return self.get_runtime_dir(runtime_id) / "profile"

    def get_runtime_state_path(self, runtime_id: str) -> Path:
        return self.get_runtime_dir(runtime_id) / "runtime-state.json"

    def get_runtime_storage_state_path(self, runtime_id: str) -> Path:
        return self.get_runtime_dir(runtime_id) / "storage-state.json"

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def source_profile_exists(self) -> bool:
        """Return True if the source profile directory exists and is non-empty."""
        path = self.source_profile_dir.expanduser()
        return path.is_dir() and any(path.iterdir())

    def load_source_state(self) -> SourceState | None:
        """Load source session metadata from disk."""
        data = self._load_json(self.source_state_path)
        if not data:
            return None
        try:
            return SourceState.model_validate(data)
        except Exception as exc:
            logger.warning("Invalid source-state.json: %s", exc)
            return None

    def write_source_state(self) -> SourceState:
        """Write a new source session generation record (after successful login)."""
        profile_path = self.source_profile_dir.expanduser().resolve()
        state = SourceState(
            version=1,
            source_runtime_id=self.runtime_id,
            login_generation=str(uuid4()),
            created_at=utcnow_iso(),
            profile_path=str(profile_path),
            cookies_path=str(self.portable_cookies_path),
        )
        self._write_json(self.source_state_path, state.model_dump())
        logger.debug("Source state written for gen: %s", state.login_generation)
        return state

    def load_runtime_state(self, runtime_id: str | None = None) -> RuntimeState | None:
        """Load metadata for a runtime session (defaults to current runtime)."""
        rid = runtime_id or self.runtime_id
        data = self._load_json(self.get_runtime_state_path(rid))
        if not data:
            return None
        try:
            return RuntimeState.model_validate(data)
        except Exception as exc:
            logger.warning("Invalid runtime-state.json for %s: %s", rid, exc)
            return None

    def write_runtime_state(
        self,
        source_state: SourceState,
        storage_state_path: Path,
        runtime_id: str | None = None,
        commit_method: str = "checkpoint_restart",
    ) -> RuntimeState:
        """Write metadata for a derived runtime session."""
        rid = runtime_id or self.runtime_id
        profile_dir = self.get_runtime_profile_dir(rid).resolve()
        now = utcnow_iso()

        state = RuntimeState(
            version=1,
            runtime_id=rid,
            source_runtime_id=source_state.source_runtime_id,
            source_login_generation=source_state.login_generation,
            created_at=now,
            committed_at=now,
            profile_path=str(profile_dir),
            storage_state_path=str(storage_state_path.resolve()),
            commit_method=commit_method,
        )
        self._write_json(self.get_runtime_state_path(rid), state.model_dump())
        return state

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def clear_runtime(self, runtime_id: str | None = None) -> bool:
        """Remove a specific runtime session directory."""
        rid = runtime_id or self.runtime_id
        target = self.get_runtime_dir(rid)
        if not target.exists():
            return True
        try:
            shutil.rmtree(target)
            return True
        except OSError as exc:
            logger.error("Failed to clear runtime %s: %s", rid, exc)
            return False

    def logout(self) -> bool:
        """Clear ALL authentication state and session artifacts."""
        targets = [
            self.source_profile_dir,
            self.portable_cookies_path,
            self.source_state_path,
            self.runtimes_root,
        ]
        success = True
        for target in targets:
            if not target.exists():
                continue
            try:
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            except OSError as exc:
                logger.error("Failed to clear %s: %s", target, exc)
                success = False
        return success

    # ------------------------------------------------------------------
    # Private runtime-id generation
    # ------------------------------------------------------------------

    def _generate_runtime_id(self) -> str:
        """Generate a deterministic environment fingerprint as runtime ID."""
        os_name = self._normalize_os(platform.system())
        arch = self._normalize_arch(platform.machine())
        kind = "container" if self._is_container() else "host"
        return f"{os_name}-{arch}-{kind}"

    @staticmethod
    def _normalize_os(system: str) -> str:
        return {"Darwin": "macos", "Linux": "linux", "Windows": "windows"}.get(
            system, system.lower()
        )

    @staticmethod
    def _normalize_arch(machine: str) -> str:
        val = machine.lower()
        if val in ("x86_64", "amd64"):
            return "amd64"
        if val in ("arm64", "aarch64"):
            return "arm64"
        return val

    @staticmethod
    def _is_container() -> bool:
        """Heuristic: detect whether we are running inside a container."""
        for p in ("/run/.containerenv", "/run/containerenv"):
            if Path(p).exists():
                return True
        markers = ("docker", "containerd", "kubepods", "podman", "libpod")
        for probe in ("/proc/1/cgroup", "/proc/self/cgroup", "/proc/1/mountinfo"):
            try:
                path = Path(probe)
                if path.exists() and any(
                    m in path.read_text().lower() for m in markers
                ):
                    return True
            except Exception:
                continue
        return False

    # ------------------------------------------------------------------
    # JSON I/O helpers (private)
    # ------------------------------------------------------------------

    def _load_json(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)  # type: ignore[no-any-return]
        except Exception as exc:
            logger.debug("Failed to load JSON from %s: %s", path, exc)
            return None

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        secure_write_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")
