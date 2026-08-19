from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


DocumentType = Literal["pdf", "csv"]


@dataclass(frozen=True, slots=True)
class SourceDocument:
    """A cleaned source unit, such as one PDF page or one CSV record."""

    source_file: str
    document_type: DocumentType
    content: str
    page: int | None = None
    record_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    """A deterministic chunk with enough provenance to locate its source."""

    id: str
    source_file: str
    document_type: DocumentType
    page: int | None
    record_number: int | None
    content: str
    content_size: int
    metadata: dict[str, Any] = field(default_factory=dict)
