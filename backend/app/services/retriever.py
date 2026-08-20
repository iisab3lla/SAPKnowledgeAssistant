from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from app.models.document import DocumentChunk
from app.services.chunker import (
    DEFAULT_CHUNKING_CONFIG,
    ChunkingConfig,
    chunk_documents,
)
from app.services.document_loader import load_csv_documents, load_pdf_documents
from app.services.source_formatter import SourceReference, format_source


MAX_QUERY_LENGTH = 500
MAX_TOP_K = 10
DEFAULT_TOP_K = 5
DEFAULT_MIN_RELEVANCE = 0.5
LOCATION_SOURCE_NAME = "company_locations.csv"
CULTURE_SOURCE_NAME = "company_culture.csv"
CONCUR_PDF_SOURCE_NAME = "sap_concur.pdf"
CONCUR_INTEGRATION_SOURCE_NAMES = frozenset(
    {"product_integrations.csv", "product_related_products.csv"}
)
CONCUR_PRIMARY_SOURCE_NAMES = frozenset(
    {
        "product_faq.csv",
        "product_features.csv",
        "product_ai_capabilities.csv",
        "product_components.csv",
        "product_deployment.csv",
        "product_licensing.csv",
        "product_use_cases.csv",
        "product_benefits.csv",
        "product_security.csv",
        "product_technologies.csv",
        CONCUR_PDF_SOURCE_NAME,
    }
)
_SECONDARY_PRODUCT_MARKERS = ("sap btp", "sap s/4hana", "sap successfactors")

_TOKEN_PATTERN = re.compile(r"[^\W_]+", flags=re.UNICODE)
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "are",
        "ao",
        "aos",
        "aonde",
        "com",
        "como",
        "da",
        "das",
        "de",
        "do",
        "dos",
        "e",
        "em",
        "essa",
        "esse",
        "esta",
        "este",
        "for",
        "how",
        "qual",
        "in",
        "is",
        "na",
        "nas",
        "no",
        "nos",
        "o",
        "of",
        "on",
        "onde",
        "os",
        "para",
        "por",
        "que",
        "se",
        "sem",
        "sobre",
        "the",
        "to",
        "um",
        "uma",
        "what",
        "where",
        "which",
        "quais",
        "fica",
        "ficam",
        "possui",
        "esta",
        "sao",
        "sap",
    }
)

_TOKEN_ALIASES = {
    "localizado": "localizacao",
    "localizada": "localizacao",
    "localizados": "localizacao",
    "localizadas": "localizacao",
    "localizacao": "localizacao",
    "localizacoes": "localizacao",
    "location": "localizacao",
    "locations": "localizacao",
    "escritorio": "escritorio",
    "escritorios": "escritorio",
    "office": "escritorio",
    "offices": "escritorio",
    "pais": "pais",
    "paises": "pais",
    "country": "pais",
    "countries": "pais",
    "brasil": "brasil",
    "brasileiro": "brasil",
    "brasileira": "brasil",
    "brasileiros": "brasil",
    "brasileiras": "brasil",
    "cidade": "cidade",
    "cidades": "cidade",
    "city": "cidade",
    "cities": "cidade",
    "presente": "presenca",
    "presenca": "presenca",
    "presence": "presenca",
    "global": "mundo",
    "mundo": "mundo",
    "culture": "cultura",
    "cultural": "cultura",
    "cultura": "cultura",
    "valor": "valor",
    "valores": "valor",
    "values": "valor",
    "value": "valor",
    "valoriza": "valor",
    "principio": "principio",
    "principios": "principio",
    "principle": "principio",
    "principles": "principio",
    "diversidade": "diversidade",
    "diversity": "diversidade",
    "diverse": "diversidade",
    "inovacao": "inovacao",
    "innovation": "inovacao",
    "inovacoes": "inovacao",
    "missao": "missao",
    "mission": "missao",
    "visao": "visao",
    "vision": "visao",
}
_LOCATION_QUERY_TERMS = frozenset(
    {"localizacao", "escritorio", "pais", "brasil", "cidade", "presenca", "mundo"}
)
_CULTURE_QUERY_TERMS = frozenset(
    {"cultura", "valor", "principio", "diversidade", "inovacao", "missao", "visao"}
)


@dataclass(frozen=True, slots=True)
class RetrievalConfig:
    max_query_length: int = MAX_QUERY_LENGTH
    default_top_k: int = DEFAULT_TOP_K
    max_top_k: int = MAX_TOP_K
    min_relevance: float = DEFAULT_MIN_RELEVANCE

    def __post_init__(self) -> None:
        if self.max_query_length <= 0:
            raise ValueError("max_query_length must be greater than zero")
        if self.default_top_k <= 0:
            raise ValueError("default_top_k must be greater than zero")
        if self.max_top_k <= 0 or self.max_top_k > MAX_TOP_K:
            raise ValueError(f"max_top_k must be between 1 and {MAX_TOP_K}")
        if self.default_top_k > self.max_top_k:
            raise ValueError("default_top_k cannot exceed max_top_k")
        if not 0 <= self.min_relevance <= 1:
            raise ValueError("min_relevance must be between zero and one")


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    chunk: DocumentChunk
    relevance: float
    source: SourceReference

    @property
    def id(self) -> str:
        return self.chunk.id

    @property
    def content(self) -> str:
        return self.chunk.content

    @property
    def metadata(self) -> dict[str, object]:
        return self.chunk.metadata


def _normalize_for_matching(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def normalize_query(query: str, max_length: int = MAX_QUERY_LENGTH) -> str:
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    if len(query) > max_length:
        raise ValueError(f"query exceeds the maximum length of {max_length} characters")
    return " ".join(_normalize_for_matching(query).split())


def _tokens(value: str) -> list[str]:
    normalized = _normalize_for_matching(value)
    return [
        _TOKEN_ALIASES.get(token, token)
        for token in _TOKEN_PATTERN.findall(normalized)
        if len(token) > 1 and token not in _STOPWORDS
    ]


def _is_location_query(query_terms: Sequence[str]) -> bool:
    return bool(_LOCATION_QUERY_TERMS.intersection(query_terms))


def _is_location_source(chunk: DocumentChunk) -> bool:
    return Path(chunk.source_file).name.casefold() == LOCATION_SOURCE_NAME


def _is_culture_query(query_terms: Sequence[str]) -> bool:
    if _CULTURE_QUERY_TERMS.intersection(query_terms):
        return True
    return {"ambiente", "trabalho"}.issubset(query_terms) or {
        "bem",
        "estar",
    }.issubset(query_terms)


def _is_culture_source(chunk: DocumentChunk) -> bool:
    return Path(chunk.source_file).name.casefold() == CULTURE_SOURCE_NAME


def _chunk_source_name(chunk: DocumentChunk) -> str:
    return Path(chunk.source_file).name.casefold()


def _chunk_mentions_concur(chunk: DocumentChunk) -> bool:
    if _chunk_source_name(chunk) == CONCUR_PDF_SOURCE_NAME:
        return True
    normalized = _normalize_for_matching(chunk.content)
    return "sap_concur" in normalized or "sap concur" in normalized


def _contains_secondary_product(chunk: DocumentChunk) -> bool:
    normalized = _normalize_for_matching(chunk.content)
    return any(marker in normalized for marker in _SECONDARY_PRODUCT_MARKERS)


def _is_concur_query(query_terms: Sequence[str]) -> bool:
    return "concur" in query_terms


def _is_concur_integration_query(query_terms: Sequence[str]) -> bool:
    return bool(
        {"integra", "integracao", "conecta", "conectores"}.intersection(query_terms)
    )


def _concur_source_priority(chunk: DocumentChunk, integration_query: bool) -> int:
    source_name = _chunk_source_name(chunk)
    if integration_query:
        if source_name in CONCUR_INTEGRATION_SOURCE_NAMES:
            return 4
        if source_name == "product_faq.csv":
            return 3
        if source_name == CONCUR_PDF_SOURCE_NAME:
            return 2
        return 1
    if source_name == "product_faq.csv" or source_name == CONCUR_PDF_SOURCE_NAME:
        return 4
    return 2


def lexical_relevance(query_terms: Sequence[str], content: str) -> float:
    """Score term coverage and capped frequency in the range [0, 1]."""

    unique_terms = tuple(dict.fromkeys(query_terms))
    if not unique_terms:
        return 0.0

    content_counts = Counter(_tokens(content))
    matched_terms = [term for term in unique_terms if content_counts[term] > 0]
    coverage = len(matched_terms) / len(unique_terms)
    capped_frequency = sum(min(content_counts[term], 3) / 3 for term in unique_terms)
    frequency = capped_frequency / len(unique_terms)
    return (coverage * 0.75) + (frequency * 0.25)


def _matched_term_count(query_terms: Sequence[str], content: str) -> int:
    query_set = set(query_terms)
    return len(query_set.intersection(_tokens(content)))


def load_knowledge_base_chunks(
    knowledge_base_root: str | Path = "knowledge_base",
    chunking_config: ChunkingConfig = DEFAULT_CHUNKING_CONFIG,
) -> list[DocumentChunk]:
    """Load and chunk the local PDF and CSV sources in stable path order."""

    root = Path(knowledge_base_root)
    if not root.exists():
        raise FileNotFoundError(f"Knowledge Base not found: {root}")

    chunks: list[DocumentChunk] = []
    for pdf_path in sorted((root / "pdf").glob("*.pdf")):
        chunks.extend(chunk_documents(load_pdf_documents(pdf_path), chunking_config))
    for csv_path in sorted((root / "csv").glob("*.csv")):
        chunks.extend(chunk_documents(load_csv_documents(csv_path), chunking_config))
    return chunks


class Retriever:
    def __init__(
        self,
        chunks: Iterable[DocumentChunk],
        config: RetrievalConfig = RetrievalConfig(),
    ) -> None:
        self._chunks = tuple(chunks)
        self.config = config

    @classmethod
    def from_knowledge_base(
        cls,
        knowledge_base_root: str | Path = "knowledge_base",
        config: RetrievalConfig = RetrievalConfig(),
        chunking_config: ChunkingConfig = DEFAULT_CHUNKING_CONFIG,
    ) -> "Retriever":
        chunks = load_knowledge_base_chunks(knowledge_base_root, chunking_config)
        return cls(chunks, config)

    def search(self, query: str, top_k: int | None = None) -> list[RetrievalResult]:
        normalized_query = normalize_query(query, self.config.max_query_length)
        query_terms = _tokens(normalized_query)
        if not query_terms:
            return []

        requested_top_k = self.config.default_top_k if top_k is None else top_k
        if requested_top_k <= 0:
            raise ValueError("top_k must be greater than zero")
        safe_top_k = min(requested_top_k, self.config.max_top_k)

        ranked: list[tuple[float, int, DocumentChunk]] = []
        location_query = _is_location_query(query_terms)
        culture_query = _is_culture_query(query_terms)
        concur_query = _is_concur_query(query_terms)
        concur_integration_query = _is_concur_integration_query(query_terms)
        for chunk in self._chunks:
            if not chunk.content.strip():
                continue
            if culture_query and not _is_culture_source(chunk):
                continue
            if concur_query:
                source_name = _chunk_source_name(chunk)
                if not _chunk_mentions_concur(chunk):
                    continue
                if concur_integration_query:
                    if source_name not in {
                        *CONCUR_PRIMARY_SOURCE_NAMES,
                        *CONCUR_INTEGRATION_SOURCE_NAMES,
                    }:
                        continue
                elif source_name in CONCUR_INTEGRATION_SOURCE_NAMES:
                    continue
                elif _contains_secondary_product(chunk):
                    continue
            relevance = lexical_relevance(query_terms, chunk.content)
            if location_query and _is_location_source(chunk):
                relevance = min(1.0, relevance + 0.2)
            if culture_query:
                matched_terms = _matched_term_count(query_terms, chunk.content)
                relevance = max(
                    relevance,
                    min(1.0, self.config.min_relevance + (0.2 * matched_terms)),
                )
            if relevance >= self.config.min_relevance:
                priority = (
                    _concur_source_priority(chunk, concur_integration_query)
                    if concur_query
                    else 0
                )
                ranked.append((relevance, priority, chunk))

        ranked.sort(
            key=lambda item: (
                -item[0],
                -item[1],
                item[2].source_file,
                item[2].page or 0,
                item[2].record_number or 0,
                item[2].id,
            )
        )
        return [
            RetrievalResult(
                chunk=chunk,
                relevance=relevance,
                source=format_source(chunk),
            )
            for relevance, _, chunk in ranked[:safe_top_k]
        ]
