import json
import platform
import shutil
from typing import Any
from uuid import uuid4

from config import Settings, setup_logger, exists
from helpers import secure_write_text, utcnow_iso
from schema import RuntimeState, SourceState

logger = setup_logger(Settings.LOG_DIR / "browser.log", name="browser.session")


class Session:

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._runtime_id = self._generate_runtime_id()

    @property
    def runtime_id(self) -> str:
        """Unique identifier for this execution environment (OS + arch + container)."""
        return self._runtime_id

    @property
    def auth_root(self) -> Any:
        """Root directory for all auth-related files."""
        return self.settings.USER_DATA_DIR.parent

    @property
    def source_profile_dir(self) -> Any:
        """Primary browser profile directory (where the user logs in)."""
        return self.settings.USER_DATA_DIR

    @property
    def source_state_path(self) -> Any:
        """Metadata file path for the primary authenticated profile."""
        return self.auth_root / "source-state.json"

    @property
    def portable_cookies_path(self) -> Any:
        """Portable cookies file (used for multi-environment bridging)."""
        return self.auth_root / "cookies.json"

    @property
    def runtimes_root(self) -> Any:
        """Root directory for all derived runtime profiles."""
        return self.auth_root / "runtimes"

    def get_runtime_dir(self, runtime_id: str) -> Any:
        return self.runtimes_root / runtime_id

    def get_runtime_profile_dir(self, runtime_id: str) -> Any:
        return self.get_runtime_dir(runtime_id) / "profile"

    def get_runtime_state_path(self, runtime_id: str) -> Any:
        return self.get_runtime_dir(runtime_id) / "runtime-state.json"

    def get_runtime_storage_state_path(self, runtime_id: str) -> Any:
        return self.get_runtime_dir(runtime_id) / "storage-state.json"

    def source_profile_exists(self) -> bool:
        """Return True if the source profile directory exists and is non-empty."""
        path = self.source_profile_dir
        if not path.is_dir():
            return False
        return any(path.iterdir())

    def load_source_state(self) -> SourceState | None:
        """Load source session metadata from disk."""
        data = self._load_json(self.source_state_path)
        if not data:
            return None
        try:
            return SourceState.model_validate(data)
        except Exception as exc:
            logger.warning(f"Invalid source-state.json: {exc}")
            return None

    def write_source_state(self) -> SourceState:
        """Write a new source session generation record (after successful login)."""
        profile_path = self.source_profile_dir.resolve()
        state = SourceState(
            version=1,
            source_runtime_id=self.runtime_id,
            login_generation=str(uuid4()),
            created_at=utcnow_iso(),
            profile_path=str(profile_path),
            cookies_path=str(self.portable_cookies_path),
        )
        self._write_json(self.source_state_path, state.model_dump())
        logger.debug(f"Source state written for gen: {state.login_generation}")
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
            logger.warning(f"Invalid runtime-state.json for {rid}: {exc}")
            return None

    def write_runtime_state(
        self,
        source_state: SourceState,
        storage_state_path: Any,
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
            logger.error(f"Failed to clear runtime {rid}: {exc}")
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
                logger.error(f"Failed to clear {target}: {exc}")
                success = False
        return success

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
            if exists(p):
                return True
        markers = ("docker", "containerd", "kubepods", "podman", "libpod")
        for probe in ("/proc/1/cgroup", "/proc/self/cgroup", "/proc/1/mountinfo"):
            try:
                if exists(probe):
                    with open(probe, "r", encoding="utf-8") as f:
                        content = f.read().lower()
                        if any(m in content for m in markers):
                            return True
            except Exception:
                continue
        return False

    def _load_json(self, path: Any) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)  # type: ignore[no-any-return]
        except Exception as exc:
            logger.debug(f"Failed to load JSON from {path}: {exc}")
            return None

    def _write_json(self, path: Any, data: dict[str, Any]) -> None:
        ensure_dir(str(path.parent))
        secure_write_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")
