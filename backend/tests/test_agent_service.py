from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.models.document import DocumentChunk
from app.services.agent_service import (
    GEMINI_AUTHENTICATION_MESSAGE,
    GEMINI_CONNECTION_MESSAGE,
    GEMINI_CONFIGURATION_MESSAGE,
    GEMINI_ERROR_MESSAGE,
    GEMINI_QUOTA_MESSAGE,
    GEMINI_TIMEOUT_MESSAGE,
    GEMINI_UNAVAILABLE_MESSAGE,
    NO_CONTEXT_MESSAGE,
    AgentInputError,
    AgentService,
)
from app.services.gemini_service import (
    GeminiAuthenticationError,
    GeminiConnectionError,
    GeminiConfigurationError,
    GeminiHTTPError,
    GeminiQuotaError,
    GeminiServiceError,
    GeminiTimeoutError,
    GeminiUnavailableError,
)
from app.services.retriever import RetrievalResult
from app.services.source_formatter import SourceReference


def make_result(chunk_id: str = "chunk-1") -> RetrievalResult:
    chunk = DocumentChunk(
        id=chunk_id,
        source_file="knowledge_base/pdf/sap_btp.pdf",
        document_type="pdf",
        page=2,
        record_number=None,
        content="SAP BTP oferece capacidades de integração e desenvolvimento.",
        content_size=60,
        metadata={"file_name": "sap_btp.pdf", "page_count": 17},
    )
    source = SourceReference(
        file_name="sap_btp.pdf",
        document_type="pdf",
        page=2,
        record_number=None,
        line_number=None,
        chunk_id=chunk_id,
    )
    return RetrievalResult(chunk=chunk, relevance=1.0, source=source)


class AgentServiceTests(unittest.TestCase):
    def test_no_local_result_does_not_call_gemini(self) -> None:
        retriever = MagicMock()
        retriever.search.return_value = []
        gemini = MagicMock()
        service = AgentService(retriever=retriever, gemini_service=gemini)

        response = service.ask("pergunta sem contexto")

        self.assertEqual(response["answer"], NO_CONTEXT_MESSAGE)
        self.assertEqual(response["sources"], [])
        self.assertFalse(response["used_ai"])
        retriever.search.assert_called_once_with("pergunta sem contexto", top_k=3)
        gemini.generate_text.assert_not_called()

    def test_culture_question_without_culture_context_does_not_call_gemini(self) -> None:
        retriever = MagicMock()
        retriever.search.return_value = []
        gemini = MagicMock()
        service = AgentService(retriever=retriever, gemini_service=gemini)

        response = service.ask("Quais são os valores da SAP?")

        self.assertEqual(response["answer"], NO_CONTEXT_MESSAGE)
        self.assertEqual(response["sources"], [])
        gemini.generate_text.assert_not_called()

    def test_local_context_calls_gemini_once_with_only_retrieved_chunks(self) -> None:
        retriever = MagicMock()
        retriever.search.return_value = [make_result()]
        gemini = MagicMock()
        gemini.generate_text.return_value = "Resposta baseada no contexto local."
        service = AgentService(retriever=retriever, gemini_service=gemini)

        response = service.ask("O que é SAP BTP?")

        self.assertEqual(response["answer"], "Resposta baseada no contexto local.")
        self.assertTrue(response["used_ai"])
        self.assertEqual(response["sources"][0]["chunk_id"], "chunk-1")
        gemini.generate_text.assert_called_once()
        prompt = gemini.generate_text.call_args.args[0]
        self.assertIn("SAP BTP oferece", prompt)
        self.assertNotIn("Knowledge Base inteira", prompt)

    def test_gemini_answer_is_formatted_for_display(self) -> None:
        retriever = MagicMock()
        retriever.search.return_value = [make_result()]
        gemini = MagicMock()
        gemini.generate_text.return_value = '''```json
{"answer": "## SAP BTP\\n\\nO **SAP BTP** permite `integrar` sistemas.", "sources": []}
```'''
        service = AgentService(retriever=retriever, gemini_service=gemini)

        response = service.ask("O que é SAP BTP?")

        self.assertEqual(
            response["answer"],
            "SAP BTP\n\nO SAP BTP permite integrar sistemas.",
        )

    def test_prompt_requires_natural_answer_without_internal_details(self) -> None:
        retriever = MagicMock()
        retriever.search.return_value = [make_result()]
        gemini = MagicMock()
        gemini.generate_text.return_value = "Resposta natural."
        service = AgentService(retriever=retriever, gemini_service=gemini)

        service.ask("O que é SAP BTP?")

        prompt = gemini.generate_text.call_args.args[0]
        self.assertIn("Não use JSON", prompt)
        self.assertIn("As fontes serão exibidas separadamente", prompt)
        self.assertIn("aproveite o que estiver disponível", prompt)
        self.assertIn("não transforme uma resposta parcial em recusa", prompt)

    def test_gemini_error_returns_controlled_response_with_sources(self) -> None:
        retriever = MagicMock()
        retriever.search.return_value = [make_result()]
        gemini = MagicMock()
        gemini.generate_text.side_effect = GeminiHTTPError("service error")
        service = AgentService(retriever=retriever, gemini_service=gemini)

        response = service.ask("O que é SAP BTP?")

        self.assertEqual(response["answer"], GEMINI_ERROR_MESSAGE)
        self.assertTrue(response["used_ai"])
        self.assertEqual(response["sources"][0]["file_name"], "sap_btp.pdf")
        gemini.generate_text.assert_called_once()

    def test_gemini_failures_are_user_friendly_and_preserve_sources(self) -> None:
        cases = (
            (GeminiQuotaError("quota"), GEMINI_QUOTA_MESSAGE),
            (GeminiAuthenticationError("forbidden"), GEMINI_AUTHENTICATION_MESSAGE),
            (GeminiTimeoutError("timeout"), GEMINI_TIMEOUT_MESSAGE),
            (GeminiUnavailableError("unavailable"), GEMINI_UNAVAILABLE_MESSAGE),
            (GeminiConnectionError("connection"), GEMINI_CONNECTION_MESSAGE),
            (GeminiServiceError("generic"), GEMINI_ERROR_MESSAGE),
        )

        for error, expected_message in cases:
            with self.subTest(error=type(error).__name__):
                retriever = MagicMock()
                retriever.search.return_value = [make_result()]
                gemini = MagicMock()
                gemini.generate_text.side_effect = error
                service = AgentService(retriever=retriever, gemini_service=gemini)

                response = service.ask("O que é SAP BTP?")

                self.assertEqual(response["answer"], expected_message)
                self.assertEqual(response["sources"][0]["file_name"], "sap_btp.pdf")
                gemini.generate_text.assert_called_once()

    def test_missing_api_key_is_controlled_without_gemini_call(self) -> None:
        retriever = MagicMock()
        retriever.search.return_value = [make_result()]
        gemini_factory = MagicMock(side_effect=GeminiConfigurationError("missing key"))
        service = AgentService(retriever=retriever, gemini_factory=gemini_factory)

        response = service.ask("O que é SAP BTP?")

        self.assertEqual(response["answer"], GEMINI_CONFIGURATION_MESSAGE)
        self.assertEqual(response["sources"][0]["file_name"], "sap_btp.pdf")
        gemini_factory.assert_called_once()

    def test_gemini_service_errors_do_not_make_a_second_call(self) -> None:
        retriever = MagicMock()
        retriever.search.return_value = [make_result()]
        gemini = MagicMock()
        gemini.generate_text.side_effect = GeminiQuotaError("quota")
        service = AgentService(retriever=retriever, gemini_service=gemini)

        service.ask("O que é SAP BTP?")

        gemini.generate_text.assert_called_once()

    def test_invalid_or_empty_question_is_rejected(self) -> None:
        retriever = MagicMock()
        service = AgentService(retriever=retriever, gemini_service=MagicMock())

        with self.assertRaises(AgentInputError):
            service.ask("")
        with self.assertRaises(AgentInputError):
            service.ask("   ")
        retriever.search.assert_not_called()

    def test_chat_endpoint_returns_contract_without_real_gemini_call(self) -> None:
        agent = MagicMock()
        agent.ask.return_value = {
            "answer": "Resposta local",
            "sources": [],
            "used_ai": False,
        }
        import app.main as main_module

        original_factory = main_module.get_agent_service
        main_module.get_agent_service = lambda: agent
        try:
            response = TestClient(app).post("/api/chat", json={"message": "teste"})
        finally:
            main_module.get_agent_service = original_factory

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), agent.ask.return_value)
        agent.ask.assert_called_once_with("teste")

    def test_chat_endpoint_rejects_empty_question(self) -> None:
        response = TestClient(app).post("/api/chat", json={"message": ""})

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
