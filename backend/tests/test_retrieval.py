from __future__ import annotations

import unittest
from pathlib import Path

from app.services.chunker import ChunkingConfig
from app.services.retriever import (
    MAX_QUERY_LENGTH,
    MAX_TOP_K,
    RetrievalConfig,
    Retriever,
    load_knowledge_base_chunks,
)
from app.services.source_formatter import format_source


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.chunks = load_knowledge_base_chunks(
            PROJECT_ROOT / "knowledge_base",
            ChunkingConfig(chunk_size=500, chunk_overlap=50),
        )
        cls.retriever = Retriever(
            cls.chunks,
            RetrievalConfig(default_top_k=5, max_top_k=MAX_TOP_K, min_relevance=0.5),
        )

    def test_concur_question_returns_relevant_context(self) -> None:
        results = self.retriever.search("What is SAP Concur?", top_k=3)

        self.assertTrue(results)
        self.assertTrue(any("concur" in result.content.casefold() for result in results))
        self.assertTrue(any("sap_concur" in result.content.casefold() for result in results))

    def test_btp_question_returns_relevant_context(self) -> None:
        results = self.retriever.search("SAP BTP", top_k=3)

        self.assertTrue(results)
        self.assertTrue(any("sap_btp" in result.content.casefold() for result in results))

    def test_results_preserve_chunk_metadata_and_source_metadata(self) -> None:
        result = self.retriever.search("SAP Concur", top_k=1)[0]

        self.assertEqual(result.metadata, result.chunk.metadata)
        self.assertEqual(result.source.chunk_id, result.chunk.id)
        self.assertEqual(result.source.document_type, result.chunk.document_type)
        self.assertIsNotNone(result.source.record_number)
        self.assertTrue(result.source.file_name)

    def test_ordering_is_deterministic(self) -> None:
        first = self.retriever.search("SAP BTP", top_k=5)
        second = self.retriever.search("SAP BTP", top_k=5)

        self.assertEqual(
            [(result.id, result.relevance) for result in first],
            [(result.id, result.relevance) for result in second],
        )

    def test_top_k_is_respected_and_capped(self) -> None:
        results = self.retriever.search("SAP", top_k=2)
        capped_results = self.retriever.search("SAP", top_k=MAX_TOP_K + 100)

        self.assertLessEqual(len(results), 2)
        self.assertLessEqual(len(capped_results), MAX_TOP_K)

    def test_query_without_context_returns_empty_list(self) -> None:
        self.assertEqual(self.retriever.search("quantum entanglement on mars"), [])

    def test_excessively_large_query_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.retriever.search("SAP " + ("context " * MAX_QUERY_LENGTH))

    def test_sources_are_formatted_without_invented_urls(self) -> None:
        pdf_chunk = next(
            chunk for chunk in self.chunks if chunk.source_file.endswith("sap_btp.pdf")
        )
        source = format_source(pdf_chunk)
        source_dict = source.as_dict()

        self.assertEqual(source.file_name, "sap_btp.pdf")
        self.assertEqual(source.document_type, "pdf")
        self.assertIsNotNone(source.page)
        self.assertEqual(source.chunk_id, pdf_chunk.id)
        self.assertNotIn("url", source_dict)
        self.assertNotIn("source_url", source_dict)


if __name__ == "__main__":
    unittest.main()
