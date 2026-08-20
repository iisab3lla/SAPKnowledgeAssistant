from __future__ import annotations

import unittest
from pathlib import Path

import app.services.retriever as retriever_module
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

    def test_brazil_location_question_returns_company_locations(self) -> None:
        results = self.retriever.search("Aonde a SAP está localizada no Brasil?", top_k=5)

        self.assertTrue(results)
        self.assertTrue(any(result.source.file_name == "company_locations.csv" for result in results))
        self.assertTrue(any(result.source.record_number == 8 for result in results))

    def test_office_variations_return_company_locations(self) -> None:
        queries = (
            "Onde ficam os escritórios da SAP no Brasil?",
            "Em quais cidades brasileiras a SAP possui presença?",
            "Onde a SAP está presente no mundo?",
        )

        for query in queries:
            with self.subTest(query=query):
                results = self.retriever.search(query, top_k=5)
                self.assertTrue(results)
                self.assertTrue(
                    any(result.source.file_name == "company_locations.csv" for result in results)
                )

    def test_location_term_normalization_preserves_semantic_terms(self) -> None:
        self.assertIn("localizacao", retriever_module._tokens("localizada localizações"))
        self.assertIn("escritorio", retriever_module._tokens("escritórios office"))
        self.assertIn("brasil", retriever_module._tokens("brasileiras"))
        self.assertIn("pais", retriever_module._tokens("países country"))
        self.assertIn("cidade", retriever_module._tokens("cidades city"))

    def test_company_culture_questions_use_only_culture_sources(self) -> None:
        queries = (
            "Quais são os valores da SAP?",
            "Como é a cultura da SAP?",
            "A SAP valoriza diversidade?",
            "Quais são os princípios da SAP?",
        )

        for query in queries:
            with self.subTest(query=query):
                results = self.retriever.search(query, top_k=5)
                self.assertTrue(results)
                self.assertTrue(
                    all(result.source.file_name == "company_culture.csv" for result in results)
                )
                self.assertFalse(
                    any("preço" in result.content.casefold() for result in results)
                )

    def test_product_price_question_does_not_use_culture_sources(self) -> None:
        results = self.retriever.search("Qual é o preço do SAP S/4HANA?", top_k=5)

        self.assertTrue(results)
        self.assertTrue(any(result.source.file_name == "product_faq.csv" for result in results))
        self.assertTrue(all(result.source.file_name != "company_culture.csv" for result in results))

    def test_sap_alone_is_not_relevant_context(self) -> None:
        self.assertEqual(self.retriever.search("SAP"), [])

    def test_concur_overview_questions_prioritize_direct_product_sources(self) -> None:
        queries = (
            "Como funciona o SAP Concur?",
            "O que é o SAP Concur?",
            "Quais recursos o SAP Concur oferece?",
        )
        unrelated_product_markers = ("sap_btp.pdf", "sap_s4hana.pdf", "sap_successfactors.pdf")

        for query in queries:
            with self.subTest(query=query):
                results = self.retriever.search(query, top_k=5)
                self.assertTrue(results)
                self.assertTrue(
                    any(result.source.file_name == "product_faq.csv" for result in results)
                )
                self.assertFalse(
                    any(
                        result.source.file_name in unrelated_product_markers
                        for result in results
                    )
                )

    def test_concur_integration_question_uses_integration_sources(self) -> None:
        results = self.retriever.search(
            "Com quais produtos o SAP Concur se integra?", top_k=8
        )

        source_names = {result.source.file_name for result in results}
        self.assertTrue(results)
        self.assertTrue(
            {"product_integrations.csv", "product_related_products.csv"}.intersection(
                source_names
            )
        )
        self.assertNotIn("sap_btp.pdf", source_names)
        self.assertNotIn("sap_s4hana.pdf", source_names)
        self.assertNotIn("sap_successfactors.pdf", source_names)

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
