from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.models.document import DocumentChunk


@dataclass(frozen=True, slots=True)
class SourceReference:
    """Traceable source information derived only from a document chunk."""

    file_name: str
    document_type: str
    page: int | None
    record_number: int | None
    line_number: int | None
    chunk_id: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def format_source(chunk: DocumentChunk) -> SourceReference:
    """Create a source reference without adding URLs or unverified data."""

    metadata = chunk.metadata
    metadata_file_name = metadata.get("file_name")
    file_name = (
        metadata_file_name
        if isinstance(metadata_file_name, str) and metadata_file_name
        else Path(chunk.source_file).name
    )
    metadata_line_number = metadata.get("line_number")
    line_number = metadata_line_number if isinstance(metadata_line_number, int) else None

    return SourceReference(
        file_name=file_name,
        document_type=chunk.document_type,
        page=chunk.page,
        record_number=chunk.record_number,
        line_number=line_number,
        chunk_id=chunk.id,
    )


def format_sources(chunks: list[DocumentChunk]) -> list[SourceReference]:
    return [format_source(chunk) for chunk in chunks]
