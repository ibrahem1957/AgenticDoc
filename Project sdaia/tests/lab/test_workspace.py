from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from lab.core.workspace import WorkspaceError, WorkspaceManager


def test_create_attach_recent_and_end(settings) -> None:
    manager = WorkspaceManager(settings)
    created = manager.create()
    assert manager.attach(created.workspace_id).workspace_id == created.workspace_id
    assert created.workspace_id in [item.workspace_id for item in manager.list_recent()]
    manager.end(created.workspace_id)
    assert not manager.path(created.workspace_id).exists()


def test_paths_reject_traversal(settings) -> None:
    manager = WorkspaceManager(settings)
    for bad in ("../outside", "ws_../../outside", "other"):
        with pytest.raises(WorkspaceError):
            manager.path(bad)


def test_ttl_sweep_uses_injected_clock(settings) -> None:
    current = datetime(2026, 1, 1, tzinfo=timezone.utc)
    manager = WorkspaceManager(settings, clock=lambda: current)
    created = manager.create()
    current += timedelta(hours=settings.workspace_ttl_hours + 1)
    assert manager.sweep_expired() == [created.workspace_id]
    assert not manager.path(created.workspace_id).exists()


def test_invalid_configured_root_has_clear_error(settings, tmp_path) -> None:
    root_file = tmp_path / "not-a-directory"
    root_file.write_text("x", encoding="utf-8")
    with pytest.raises(WorkspaceError, match="configured LAB_TMP_DIR root"):
        WorkspaceManager(replace(settings, tmp_dir=str(root_file)))
