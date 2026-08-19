from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable

from app.models.document import DocumentChunk, SourceDocument
from app.services.document_loader import clean_text


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    """Central deterministic configuration for character-based chunking."""

    chunk_size: int = 1000
    chunk_overlap: int = 100

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")


DEFAULT_CHUNKING_CONFIG = ChunkingConfig()


def _stable_chunk_id(
    document: SourceDocument,
    chunk_index: int,
    content: str,
) -> str:
    identity = {
        "source_file": document.source_file,
        "document_type": document.document_type,
        "page": document.page,
        "record_number": document.record_number,
        "chunk_index": chunk_index,
        "content": content,
    }
    serialized = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _chunk_text(text: str, config: ChunkingConfig) -> Iterable[tuple[int, int, str]]:
    start = 0
    text_length = len(text)

    while start < text_length:
        limit = min(start + config.chunk_size, text_length)
        end = limit

        if limit < text_length:
            newline_boundary = text.rfind("\n", start + 1, limit)
            space_boundary = text.rfind(" ", start + 1, limit)
            boundary = max(newline_boundary, space_boundary)
            if boundary > start:
                end = boundary

        content = text[start:end].strip()
        if not content:
            end = limit
            content = text[start:end].strip()
        if not content:
            start = end + 1
            continue

        yield start, end, content
        if end >= text_length:
            break

        next_start = end - config.chunk_overlap
        start = max(start + 1, next_start)


def chunk_documents(
    documents: Iterable[SourceDocument],
    config: ChunkingConfig = DEFAULT_CHUNKING_CONFIG,
) -> list[DocumentChunk]:
    """Split cleaned source documents into reproducible chunks."""

    chunks: list[DocumentChunk] = []
    for document in documents:
        content = clean_text(document.content)
        for chunk_index, (start, end, chunk_content) in enumerate(
            _chunk_text(content, config)
        ):
            metadata = dict(document.metadata)
            metadata.update(
                {
                    "chunk_index": chunk_index,
                    "chunk_start": start,
                    "chunk_end": end,
                }
            )
            chunks.append(
                DocumentChunk(
                    id=_stable_chunk_id(document, chunk_index, chunk_content),
                    source_file=document.source_file,
                    document_type=document.document_type,
                    page=document.page,
                    record_number=document.record_number,
                    content=chunk_content,
                    content_size=len(chunk_content),
                    metadata=metadata,
                )
            )

    return chunks
