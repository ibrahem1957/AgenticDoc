from __future__ import annotations

from pathlib import Path
from typing import Protocol

from lab.core.models import (
    AdapterInfo,
    CostEstimate,
    LabDocument,
    PageResult,
    RunContext,
)


def text_status(text: str) -> str:
    return "ok" if text.strip() else "empty"


class Adapter(Protocol):
    info: AdapterInfo

    def check_available(self) -> tuple[bool, str | None]: ...

    def estimate_cost(self, doc: LabDocument, pages: list[int]) -> CostEstimate: ...

    def run(
        self, pdf_path: Path, pages: list[int], params: dict, ctx: RunContext
    ) -> list[PageResult]: ...


class LocalTextAdapter:
    info: AdapterInfo

    def __init__(self, info: AdapterInfo):
        self.info = info

    def check_available(self) -> tuple[bool, str | None]:
        return True, None

    def estimate_cost(self, doc: LabDocument, pages: list[int]) -> CostEstimate:
        return CostEstimate(cost_usd=0.0, detail="Local CPU extraction")
