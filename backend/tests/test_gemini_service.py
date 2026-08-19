from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from google.genai import errors

from app.services.gemini_service import (
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT_MS,
    DOTENV_PATH,
    GeminiConfigurationError,
    GeminiHTTPError,
    GeminiQuotaError,
    GeminiService,
    GeminiTimeoutError,
    GeminiUnavailableError,
)


class GeminiServiceTests(unittest.TestCase):
    def test_missing_api_key_fails_without_constructing_client(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            client_factory = MagicMock()

            with patch("app.services.gemini_service.load_dotenv"):
                with self.assertRaises(GeminiConfigurationError):
                    GeminiService(client_factory=client_factory)

            client_factory.assert_not_called()

    def test_dotenv_path_is_loaded_without_overriding_environment(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "environment-key"}, clear=True):
            with patch("app.services.gemini_service.load_dotenv") as load_dotenv:
                GeminiService(client_factory=MagicMock())

                load_dotenv.assert_called_once_with(dotenv_path=DOTENV_PATH, override=False)

    def test_default_and_environment_model_configuration(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            service = GeminiService(client_factory=MagicMock())
            self.assertEqual(service.config.model, DEFAULT_MODEL)

        with patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "custom-model"},
            clear=True,
        ):
            service = GeminiService(client_factory=MagicMock())
            self.assertEqual(service.config.model, "custom-model")

    def test_single_mocked_call_returns_only_response_text(self) -> None:
        with patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "test-model"},
            clear=True,
        ):
            client = MagicMock()
            client.models.generate_content.return_value = SimpleNamespace(text="mock response")
            client_factory = MagicMock(return_value=client)

            result = GeminiService(client_factory=client_factory).generate_text("short prompt")

            self.assertEqual(result, "mock response")
            client_factory.assert_called_once()
            client.models.generate_content.assert_called_once_with(
                model="test-model",
                contents="short prompt",
            )
            options = client_factory.call_args.kwargs["http_options"]
            self.assertEqual(options.timeout, DEFAULT_TIMEOUT_MS)
            self.assertEqual(options.retry_options.attempts, 1)
            client.close.assert_called_once()

    def test_api_errors_are_mapped_without_exposing_details(self) -> None:
        error_cases = (
            (429, GeminiQuotaError),
            (408, GeminiTimeoutError),
            (503, GeminiUnavailableError),
            (400, GeminiHTTPError),
        )

        for status_code, expected_error in error_cases:
            with self.subTest(status_code=status_code):
                with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
                    client = MagicMock()
                    client.models.generate_content.side_effect = errors.APIError(
                        status_code,
                        {"error": {"message": "redacted test detail"}},
                    )
                    service = GeminiService(client_factory=MagicMock(return_value=client))

                    with self.assertRaises(expected_error) as raised:
                        service.generate_text("short prompt")

                    self.assertNotIn("test-key", str(raised.exception))

    def test_timeout_exception_is_mapped(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            client = MagicMock()
            client.models.generate_content.side_effect = TimeoutError()
            service = GeminiService(client_factory=MagicMock(return_value=client))

            with self.assertRaises(GeminiTimeoutError):
                service.generate_text("short prompt")

    def test_prompt_limits_are_enforced(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            client_factory = MagicMock()
            service = GeminiService(client_factory=client_factory)

            with self.assertRaises(ValueError):
                service.generate_text("x" * 4_001)

            client_factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
