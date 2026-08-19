from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.models.document import DocumentChunk
from app.services.agent_service import (
    GEMINI_ERROR_MESSAGE,
    NO_CONTEXT_MESSAGE,
    AgentInputError,
    AgentService,
)
from app.services.gemini_service import GeminiHTTPError
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
