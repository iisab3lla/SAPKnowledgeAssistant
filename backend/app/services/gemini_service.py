from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import httpx
from google import genai
from google.genai import errors, types
from dotenv import load_dotenv


DEFAULT_MODEL = "gemini-3.5-flash-lite"
DEFAULT_TIMEOUT_MS = 10_000
MAX_PROMPT_LENGTH = 4_000
DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class GeminiServiceError(RuntimeError):
    """Base error for the isolated Gemini service."""


class GeminiConfigurationError(GeminiServiceError):
    """Raised when the required environment configuration is missing."""


class GeminiTimeoutError(GeminiServiceError):
    """Raised when the Gemini request exceeds its timeout."""


class GeminiQuotaError(GeminiServiceError):
    """Raised when Gemini rejects a request because of quota or rate limits."""


class GeminiUnavailableError(GeminiServiceError):
    """Raised when the Gemini service or network is unavailable."""


class GeminiHTTPError(GeminiServiceError):
    """Raised for non-retryable HTTP errors returned by Gemini."""


@dataclass(frozen=True, slots=True)
class GeminiConfig:
    api_key: str
    model: str = DEFAULT_MODEL
    timeout_ms: int = DEFAULT_TIMEOUT_MS


def load_gemini_config() -> GeminiConfig:
    """Read Gemini configuration exclusively from process environment variables."""

    load_dotenv(dotenv_path=DOTENV_PATH, override=False)
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise GeminiConfigurationError("GEMINI_API_KEY is not configured.")

    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    return GeminiConfig(api_key=api_key, model=model)


def _api_error_code(error: errors.APIError) -> int | None:
    code = getattr(error, "code", None)
    return code if isinstance(code, int) else None


class GeminiService:
    """A single-call Gemini client with no RAG, file, or retry integration."""

    def __init__(self, client_factory=None) -> None:
        self.config = load_gemini_config()
        self._client_factory = client_factory or genai.Client

    def generate_text(self, prompt: str) -> str:
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string")
        if not prompt.strip():
            raise ValueError("prompt cannot be empty")
        if len(prompt) > MAX_PROMPT_LENGTH:
            raise ValueError(
                f"prompt exceeds the maximum length of {MAX_PROMPT_LENGTH} characters"
            )

        client = None
        try:
            client = self._client_factory(
                api_key=self.config.api_key,
                http_options=types.HttpOptions(
                    timeout=self.config.timeout_ms,
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            )
            response = client.models.generate_content(
                model=self.config.model,
                contents=prompt,
            )
            response_text = getattr(response, "text", None)
            if not isinstance(response_text, str) or not response_text.strip():
                raise GeminiServiceError("Gemini returned no text response.")
            return response_text
        except GeminiServiceError:
            raise
        except errors.APIError as error:
            self._raise_api_error(error)
        except (httpx.TimeoutException, TimeoutError) as error:
            raise GeminiTimeoutError("Gemini request timed out.") from error
        except (httpx.NetworkError, OSError) as error:
            raise GeminiUnavailableError("Gemini service is unavailable.") from error
        except Exception as error:
            raise GeminiServiceError("Gemini request failed.") from error
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass

    @staticmethod
    def _raise_api_error(error: errors.APIError) -> None:
        status_code = _api_error_code(error)
        if status_code == 429:
            raise GeminiQuotaError("Gemini quota or rate limit was exceeded.") from error
        if status_code in {408, 504}:
            raise GeminiTimeoutError("Gemini request timed out.") from error
        if status_code is not None and status_code >= 500:
            raise GeminiUnavailableError("Gemini service is unavailable.") from error
        raise GeminiHTTPError("Gemini request was rejected.") from error
