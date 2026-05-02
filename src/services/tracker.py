import asyncio
import json
import os
import tempfile
from datetime import datetime
from typing import Any

from schema import StatusType, TrackedApplication
from helpers import sanitize_filename
from config import Settings, setup_logger, exists, delete

logger = setup_logger(Settings.LOG_DIR / "tracker_service.log", name="linkedin-mcp.services.tracker")


class ApplicationTrackerService:
    """Tracks job applications locally via JSON files."""

    def __init__(self, data_dir: Any) -> None:
        self._dir = data_dir / "applications"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Any:
        """Get the path for an application tracking file."""
        safe_id = sanitize_filename(job_id)
        result = self._dir / f"{safe_id}.json"
        # Since we use Path objects from Settings, .resolve() and .is_relative_to work
        if not result.resolve().is_relative_to(self._dir.resolve()):
            raise ValueError(f"Invalid job ID for path: {job_id}")
        return result

    async def track_application(
        self, application: TrackedApplication
    ) -> TrackedApplication:
        """Add or update a tracked application."""
        application.updated_at = datetime.now().isoformat()
        path = self._path(application.job_id)

        def _write() -> None:
            fd, tmp_path = tempfile.mkstemp(dir=str(self._dir), suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(application.model_dump(), f, indent=2, default=str)
                os.replace(tmp_path, str(path))
                logger.info(f"Tracked application saved: {application.job_id}")
            except Exception as exc:
                if exists(tmp_path):
                    delete(tmp_path)
                logger.error(f"Failed to write application {application.job_id}: {exc}")
                raise

        await asyncio.to_thread(_write)
        return application

    async def get_application(self, job_id: str) -> TrackedApplication | None:
        path = self._path(job_id)

        def _read() -> dict[str, Any] | None:
            if not path.exists():
                return None
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as exc:
                logger.debug(f"Failed to read application {job_id}: {exc}")
                return None

        data = await asyncio.to_thread(_read)
        return TrackedApplication(**data) if data else None

    async def list_applications(
        self, status: str | None = None
    ) -> list[TrackedApplication]:
        def _list() -> list[dict[str, Any]]:
            results: list[dict[str, Any]] = []
            if not self._dir.exists():
                return results
            
            # glob returns Path objects, we use .stat()
            for f in sorted(
                self._dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
            ):
                try:
                    with open(f, "r", encoding="utf-8") as fh:
                        results.append(json.load(fh))
                except Exception:
                    continue
            return results

        apps: list[TrackedApplication] = []
        for data in await asyncio.to_thread(_list):
            try:
                apps.append(TrackedApplication(**data))
            except Exception:
                continue

        if status:
            apps = [a for a in apps if a.status == status]
        return apps

    async def update_status(
        self, job_id: str, status: StatusType, notes: str = ""
    ) -> TrackedApplication:
        app = await self.get_application(job_id)
        if not app:
            raise ValueError(f"No tracked application for {job_id}")
        app.status = status
        if notes:
            app.notes = notes
        return await self.track_application(app)


# ── Registry Convention ───────────────────────────────────────────────────────
from helpers.registry import ServiceMeta
SERVICE = ServiceMeta(
    attr="tracker",
    cls=ApplicationTrackerService,
    lazy=False,
    factory=lambda ctx: ApplicationTrackerService(ctx.settings.DATA_DIR),
)
