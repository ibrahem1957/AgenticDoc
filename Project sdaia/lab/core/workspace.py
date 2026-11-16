from __future__ import annotations

import json
import os
import secrets
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from lab.core.models import WorkspaceRecord
from lab.core.settings import LabSettings


class WorkspaceError(ValueError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WorkspaceManager:
    def __init__(self, settings: LabSettings, clock: Callable[[], datetime] = utc_now):
        configured = settings.tmp_dir.strip()
        self.root = (
            Path(configured)
            if configured
            else Path(tempfile.gettempdir()) / "agenticdoc-lab"
        )
        self.root = self.root.resolve()
        try:
            self.root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise WorkspaceError(
                f"Cannot create configured LAB_TMP_DIR root '{self.root}': {exc}"
            ) from exc
        self.settings = settings
        self.clock = clock

    def _validate_id(self, workspace_id: str) -> None:
        if (
            not workspace_id.startswith("ws_")
            or not workspace_id[3:].replace("-", "").replace("_", "").isalnum()
        ):
            raise WorkspaceError("Invalid workspace ID")

    def path(self, workspace_id: str) -> Path:
        self._validate_id(workspace_id)
        candidate = (self.root / workspace_id).resolve()
        if not candidate.is_relative_to(self.root):
            raise WorkspaceError("Workspace path escapes the configured root")
        return candidate

    @staticmethod
    def atomic_write_json(path: Path, value: dict) -> None:
        temp_path = path.with_name(f".{path.stem[:20]}.{secrets.token_hex(2)}.tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        except OSError as exc:
            temp_path.unlink(missing_ok=True)
            raise WorkspaceError(
                f"Cannot write workspace data under configured root '{path.parent}': {exc}"
            ) from exc

    def create(self) -> WorkspaceRecord:
        now = self.clock()
        record = WorkspaceRecord(
            workspace_id=f"ws_{secrets.token_urlsafe(16)}",
            created_at=now,
            updated_at=now,
            external_apis_enabled=False,
        )
        workspace_path = self.path(record.workspace_id)
        for child in ("docs", "runs", "gt", "reviews"):
            (workspace_path / child).mkdir(parents=True, exist_ok=True)
        self.atomic_write_json(
            workspace_path / "workspace.json", record.model_dump(mode="json")
        )
        return record

    def attach(self, workspace_id: str, *, touch: bool = True) -> WorkspaceRecord:
        workspace_path = self.path(workspace_id)
        metadata = workspace_path / "workspace.json"
        if not metadata.is_file():
            raise WorkspaceError("Workspace does not exist")
        record = WorkspaceRecord.model_validate_json(
            metadata.read_text(encoding="utf-8")
        )
        if touch:
            record.updated_at = self.clock()
            self.atomic_write_json(metadata, record.model_dump(mode="json"))
        return record

    def list_recent(self) -> list[WorkspaceRecord]:
        records: list[WorkspaceRecord] = []
        for metadata in self.root.glob("ws_*/workspace.json"):
            try:
                records.append(
                    WorkspaceRecord.model_validate_json(
                        metadata.read_text(encoding="utf-8")
                    )
                )
            except (OSError, ValueError):
                continue
        return sorted(records, key=lambda item: item.updated_at, reverse=True)

    def end(self, workspace_id: str) -> None:
        workspace_path = self.path(workspace_id)
        if workspace_path.exists():
            shutil.rmtree(workspace_path)

    def sweep_expired(self) -> list[str]:
        cutoff = self.clock() - timedelta(hours=self.settings.workspace_ttl_hours)
        deleted: list[str] = []
        for record in self.list_recent():
            if record.updated_at < cutoff:
                self.end(record.workspace_id)
                deleted.append(record.workspace_id)
        return deleted
