from functools import lru_cache
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.services.agent_service import AgentInputError, AgentService
from app.services.gemini_service import GeminiServiceError
from app.services.retriever import Retriever


_local_frontend_origins = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}
_configured_frontend_origins = {
    origin.strip().rstrip("/")
    for origin in os.environ.get("FRONTEND_ORIGIN", "").split(",")
    if origin.strip()
}
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(_local_frontend_origins | _configured_frontend_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    used_ai: bool


@lru_cache(maxsize=1)
def get_agent_service() -> AgentService:
    project_root = Path(__file__).resolve().parents[2]
    retriever = Retriever.from_knowledge_base(project_root / "knowledge_base")
    return AgentService(retriever=retriever)


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        response = get_agent_service().ask(request.message)
    except AgentInputError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except GeminiServiceError as error:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível processar a pergunta neste momento.",
        ) from error
    return ChatResponse(**response)
