from __future__ import annotations

import csv
import unicodedata
from pathlib import Path
from typing import Any, Iterable

from pypdf import PdfReader

from app.models.document import SourceDocument


def clean_text(value: str) -> str:
    """Normalize whitespace and remove control characters from source text."""

    value = value.replace("\ufeff", "").replace("\x00", "")
    value = "".join(
        character
        for character in value
        if character in "\r\n\t" or not unicodedata.category(character).startswith("C")
    )
    value = value.replace("\r\n", "\n").replace("\r", "\n")

    cleaned_lines = [" ".join(line.split()) for line in value.split("\n")]
    return "\n".join(line for line in cleaned_lines if line)


def _validate_file(path: str | Path, document_type: str) -> Path:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"{document_type.upper()} file not found: {file_path}")
    if not file_path.is_file():
        raise IsADirectoryError(f"Expected a file, received: {file_path}")
    if file_path.stat().st_size == 0:
        raise ValueError(f"{document_type.upper()} file is empty: {file_path}")
    return file_path


def _source_reference(path: Path) -> str:
    resolved_path = path.resolve()
    try:
        return resolved_path.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return resolved_path.as_posix()


def _base_metadata(path: Path, document_type: str) -> dict[str, Any]:
    return {
        "file_name": path.name,
        "file_extension": path.suffix.lower(),
        "document_type": document_type,
    }


def load_pdf_documents(path: str | Path) -> list[SourceDocument]:
    """Load one cleaned source document per non-empty PDF page."""

    file_path = _validate_file(path, "pdf")
    source_file = _source_reference(file_path)
    reader = PdfReader(str(file_path))
    page_count = len(reader.pages)
    documents: list[SourceDocument] = []

    for page_number, page in enumerate(reader.pages, start=1):
        content = clean_text(page.extract_text() or "")
        if not content:
            continue

        metadata = _base_metadata(file_path, "pdf")
        metadata["page_count"] = page_count
        documents.append(
            SourceDocument(
                source_file=source_file,
                document_type="pdf",
                page=page_number,
                content=content,
                metadata=metadata,
            )
        )

    return documents


def _csv_content(headers: Iterable[str], row: dict[str, str | None]) -> str:
    fields: list[str] = []
    for header in headers:
        value = clean_text(row.get(header) or "")
        if value:
            fields.append(f"{header}: {value}")
    return clean_text("\n".join(fields))


def load_csv_documents(path: str | Path) -> list[SourceDocument]:
    """Load one cleaned source document per non-empty CSV record."""

    file_path = _validate_file(path, "csv")
    source_file = _source_reference(file_path)
    documents: list[SourceDocument] = []

    with file_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames:
            return documents

        headers = [clean_text(header or "") for header in reader.fieldnames]
        if any(not header for header in headers):
            raise ValueError(f"CSV contains an empty header: {file_path}")
        if len(set(headers)) != len(headers):
            raise ValueError(f"CSV contains duplicate headers: {file_path}")

        for record_number, row in enumerate(reader, start=1):
            if row.get(None):
                raise ValueError(f"CSV record has more fields than its header: {file_path}")

            content = _csv_content(reader.fieldnames, row)
            if not content:
                continue

            metadata = _base_metadata(file_path, "csv")
            metadata.update(
                {
                    "columns": headers,
                    "record_number": record_number,
                    "line_number": reader.line_num,
                }
            )
            documents.append(
                SourceDocument(
                    source_file=source_file,
                    document_type="csv",
                    record_number=record_number,
                    content=content,
                    metadata=metadata,
                )
            )

    return documents


def load_documents(path: str | Path) -> list[SourceDocument]:
    """Dispatch to the format-specific loader using the file extension."""

    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return load_pdf_documents(path)
    if suffix == ".csv":
        return load_csv_documents(path)
    raise ValueError(f"Unsupported document type: {suffix or '(none)'}")
