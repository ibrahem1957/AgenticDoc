from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PageTag = Literal[
    "multi_column",
    "headings",
    "diacritics",
    "arabic_indic_digits",
    "western_digits",
    "mixed_ar_en",
    "header_footer",
    "footnotes",
    "tables_present",
    "images_present",
    "low_quality",
    "other",
]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1


class LabDocument(ContractModel):
    doc_id: str
    display_name: str
    kind: Literal["pdf", "image"]
    sha256: str
    size_bytes: int
    page_count: int
    page_sizes: list[tuple[float, float]]
    has_text_layer: list[bool] | None
    pdf_producer: str | None
    pdf_creator: str | None
    page_tags: dict[int, list[PageTag]] = Field(default_factory=dict)
    uploaded_at: datetime


class ComparisonSet(ContractModel):
    set_id: str
    doc_id: str
    doc_sha256: str
    pages: list[int]
    gt_versions: dict[int, int]
    run_ids: list[str]
    page_set_hash: str


class ErrorItem(ContractModel):
    run_id: str
    variant: str
    page: int
    index: int
    op: Literal["substitute", "insert", "delete", "transpose_suspect"]
    ref: str
    hyp: str
    ref_context: str
    hyp_context: str
    ref_offset: int
    hyp_offset: int
    categories: list[
        Literal[
            "digit",
            "digit_form",
            "diacritic",
            "arabic_letter",
            "presentation_form",
            "ligature",
            "latin",
            "punctuation",
            "whitespace",
            "order",
        ]
    ]


class AdapterInfo(ContractModel):
    adapter_id: str
    task: Literal["text", "ocr", "table", "chart"]
    label: str
    kind: Literal["local", "api"]
    library: str
    library_version: str | None
    license: str
    model_id: str | None
    params: dict
    available: bool
    unavailable_reason: str | None
    supports_blocks: bool
    implementation_version: str = "1"


class TextBlock(ContractModel):
    order: int
    text: str
    bbox: tuple[float, float, float, float] | None


class PageResult(ContractModel):
    page: int
    text: str
    blocks: list[TextBlock] | None
    status: Literal["ok", "empty", "error", "not_applicable"]
    error: str | None
    elapsed_ms: float | None
    overlay_ms: float | None = None
    extraction_cpu_ms: float | None = None


class UsageRecord(ContractModel):
    provider: str
    model: str | None
    engine: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    pages_billed: int | None
    cost_usd: float | None
    cost_source: Literal["response", "estimated", "unknown"]
    latency_ms: float
    request_count: int
    retries: int


class RunResult(ContractModel):
    run_id: str
    doc_id: str
    doc_sha256: str
    adapter: AdapterInfo
    variant: str
    pages: list[PageResult]
    page_mapping: Literal["exact", "approximate", "document_only"]
    started_at: datetime
    wall_ms: float
    cpu_ms: float | None
    usage: UsageRecord | None
    status: Literal["ok", "partial", "error", "timeout", "cancelled"]
    error: str | None
    cache_hit: bool
    environment: dict
    repeat_timings: list[dict[str, float | None]] = Field(default_factory=list)
    startup_ms: float = 0.0
    overlay_ms: float = 0.0


class GroundTruthPage(ContractModel):
    page: int
    text: str
    status: Literal["draft", "verified"]
    seeded_from: str | None
    verified_by: str | None
    verified_at: datetime | None
    notes: str | None


class GroundTruth(ContractModel):
    doc_id: str
    doc_sha256: str
    task: Literal["text"]
    pages: list[GroundTruthPage]
    version: int
    source: Literal["manual", "fixture", "imported"]


class MetricResult(ContractModel):
    run_id: str
    page: int | None
    gt_version: int
    cer: float
    wer: float
    cer_no_diacritics: float
    bow_f1: float
    num_recall: float | None
    num_precision: float | None
    ref_chars: int
    hyp_chars: int


class Diagnostics(ContractModel):
    run_id: str
    page: int
    chars: int
    arabic_ratio: float
    latin_ratio: float
    presentation_forms: int
    replacement_chars: int
    cid_tokens: int
    private_use_chars: int
    empty: bool
    arabic_ligatures: int
    digits_arabic_indic: int
    digits_extended: int
    digits_ascii: int
    diacritics_detached: int
    suspected_reversed_arabic: float | None


class HumanReview(ContractModel):
    run_id: str
    page: int | None
    rating: Literal["correct", "minor_issues", "major_issues", "unusable"]
    issues: list[
        Literal[
            "reversed_order",
            "wrong_column_order",
            "broken_letters",
            "missing_text",
            "extra_text",
            "numbers_changed",
            "diacritics_lost",
            "header_footer_noise",
            "merged_words",
            "split_words",
            "other",
        ]
    ]
    notes: str | None
    reviewer: str | None
    created_at: datetime


class WorkspaceRecord(ContractModel):
    workspace_id: str
    created_at: datetime
    updated_at: datetime
    external_apis_enabled: bool = False


class CostEstimate(ContractModel):
    cost_usd: float
    source: Literal["configured", "unknown"] = "configured"
    detail: str = ""


class RunContext(ContractModel):
    workspace_id: str
    repeat_index: int = 0


class ConfirmationToken(ContractModel):
    doc_sha256: str
    pages: list[int]
    adapter_id: str
    engine: str | None
    model: str | None
    estimate_usd: float
    created_at: datetime
