from __future__ import annotations

import importlib
import importlib.metadata
from dataclasses import dataclass
from typing import Any

from lab.core.models import AdapterInfo
from lab.core.settings import load_adapter_config


@dataclass(frozen=True)
class RegisteredAdapter:
    info: AdapterInfo
    module: str
    preselected: bool
    enabled: bool
    config: dict[str, Any]


class AdapterRegistry:
    def __init__(self, entries: list[dict[str, Any]] | None = None):
        self._entries: dict[str, RegisteredAdapter] = {}
        for raw in entries if entries is not None else load_adapter_config():
            self._register(raw)

    def _register(self, raw: dict[str, Any]) -> None:
        library = raw.get("library", "")
        version: str | None = None
        available = bool(raw.get("enabled", True))
        reason = None if available else "Disabled in adapters.toml"
        implementation_version = "1"
        if available and raw.get("kind") == "local":
            try:
                version = importlib.metadata.version(library)
                module = importlib.import_module(raw["module"])
                implementation_version = str(
                    getattr(module, "ADAPTER_VERSION", implementation_version)
                )
            except (ImportError, importlib.metadata.PackageNotFoundError) as exc:
                available = False
                reason = f"Dependency unavailable: {exc}"
        info = AdapterInfo(
            adapter_id=raw["id"],
            task=raw["task"],
            label=raw["label"],
            kind=raw["kind"],
            library=library,
            library_version=version,
            license=raw.get("license", "unknown"),
            model_id=raw.get("carrier_model") or None,
            params=dict(raw.get("params", {})),
            available=available,
            unavailable_reason=reason,
            supports_blocks=bool(raw.get("supports_blocks", False)),
            implementation_version=implementation_version,
        )
        self._entries[info.adapter_id] = RegisteredAdapter(
            info=info,
            module=raw["module"],
            preselected=bool(raw.get("preselected", False)),
            enabled=bool(raw.get("enabled", True)),
            config=raw,
        )

    def list(self, task: str | None = None) -> list[RegisteredAdapter]:
        entries = list(self._entries.values())
        return [entry for entry in entries if task is None or entry.info.task == task]

    def get(self, adapter_id: str) -> RegisteredAdapter:
        try:
            return self._entries[adapter_id]
        except KeyError as exc:
            raise KeyError(f"Unknown adapter: {adapter_id}") from exc

    def build(self, adapter_id: str):
        entry = self.get(adapter_id)
        if not entry.info.available:
            raise RuntimeError(entry.info.unavailable_reason or "Adapter unavailable")
        module = importlib.import_module(entry.module)
        return module.create_adapter(entry.info.model_copy(deep=True))
