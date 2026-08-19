from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from app.services.chunker import ChunkingConfig, chunk_documents
from app.services.document_loader import clean_text, load_csv_documents, load_pdf_documents


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class DocumentProcessingTests(unittest.TestCase):
    def test_text_cleaning_removes_empty_lines_and_unnecessary_whitespace(self) -> None:
        self.assertEqual(clean_text("  first  \n\n second\t\x00  "), "first\nsecond")

    def test_real_pdf_is_loaded_with_page_metadata_and_chunked(self) -> None:
        pdf_path = PROJECT_ROOT / "knowledge_base" / "pdf" / "sap_btp.pdf"

        documents = load_pdf_documents(pdf_path)
        chunks = chunk_documents(documents, ChunkingConfig(chunk_size=300, chunk_overlap=30))

        self.assertTrue(documents)
        self.assertTrue(chunks)
        self.assertTrue(all(chunk.content for chunk in chunks))
        self.assertTrue(all(chunk.content_size == len(chunk.content) for chunk in chunks))
        self.assertTrue(all(chunk.source_file.endswith("knowledge_base/pdf/sap_btp.pdf") for chunk in chunks))
        self.assertTrue(all(chunk.document_type == "pdf" for chunk in chunks))
        self.assertTrue(all(chunk.page is not None for chunk in chunks))

    def test_real_csv_is_loaded_with_record_metadata_and_chunked(self) -> None:
        csv_path = PROJECT_ROOT / "knowledge_base" / "csv" / "products.csv"

        documents = load_csv_documents(csv_path)
        chunks = chunk_documents(documents, ChunkingConfig(chunk_size=300, chunk_overlap=30))

        self.assertTrue(documents)
        self.assertTrue(chunks)
        self.assertTrue(all(chunk.content for chunk in chunks))
        self.assertTrue(all(chunk.content_size == len(chunk.content) for chunk in chunks))
        self.assertTrue(all(chunk.source_file.endswith("knowledge_base/csv/products.csv") for chunk in chunks))
        self.assertTrue(all(chunk.document_type == "csv" for chunk in chunks))
        self.assertTrue(all(chunk.record_number is not None for chunk in chunks))
        self.assertTrue(all("columns" in chunk.metadata for chunk in chunks))

    def test_chunking_is_deterministic_and_respects_size(self) -> None:
        pdf_path = PROJECT_ROOT / "knowledge_base" / "pdf" / "sap_btp.pdf"
        config = ChunkingConfig(chunk_size=240, chunk_overlap=20)

        first = chunk_documents(load_pdf_documents(pdf_path), config)
        second = chunk_documents(load_pdf_documents(pdf_path), config)

        self.assertEqual([chunk.id for chunk in first], [chunk.id for chunk in second])
        self.assertTrue(all(len(chunk.content) <= config.chunk_size for chunk in first))

    def test_missing_and_empty_files_have_explicit_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            empty_csv = temporary_path / "empty.csv"
            empty_pdf = temporary_path / "empty.pdf"
            empty_csv.touch()
            empty_pdf.touch()

            with self.assertRaises(ValueError):
                load_csv_documents(empty_csv)
            with self.assertRaises(ValueError):
                load_pdf_documents(empty_pdf)

            with self.assertRaises(FileNotFoundError):
                load_csv_documents(temporary_path / "missing.csv")
            with self.assertRaises(FileNotFoundError):
                load_pdf_documents(temporary_path / "missing.pdf")

    def test_original_documents_are_not_modified_by_processing(self) -> None:
        paths = [
            PROJECT_ROOT / "knowledge_base" / "pdf" / "sap_btp.pdf",
            PROJECT_ROOT / "knowledge_base" / "csv" / "products.csv",
        ]
        before = [hashlib.sha256(path.read_bytes()).digest() for path in paths]

        load_pdf_documents(paths[0])
        load_csv_documents(paths[1])

        after = [hashlib.sha256(path.read_bytes()).digest() for path in paths]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
