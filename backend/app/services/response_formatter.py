from __future__ import annotations

import json
import re
from typing import Any


_CODE_FENCE = re.compile(r"^```(?:json|text)?\s*|\s*```$", re.IGNORECASE)
_MARKDOWN_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+")
_EMPHASIS = re.compile(r"(\*\*|__|`)")
_TECHNICAL_FIELDS = re.compile(
    r'^\s*"?(?:answer|sources|used_ai|chunk_id|id|score|metadata)"?\s*:',
    re.IGNORECASE,
)


def format_assistant_answer(value: str) -> str:
    """Return a user-facing answer without transport or presentation artifacts."""

    text = value.strip()
    text = _CODE_FENCE.sub("", text).strip()
    text = _extract_answer_from_json(text)

    lines = []
    for line in text.splitlines():
        if _TECHNICAL_FIELDS.match(line):
            continue
        line = _MARKDOWN_HEADING.sub("", line)
        line = _EMPHASIS.sub("", line)
        lines.append(line.rstrip())

    formatted = "\n".join(lines)
    formatted = re.sub(r"\n{3,}", "\n\n", formatted).strip()
    return formatted or "Não foi possível gerar uma resposta neste momento."


def _extract_answer_from_json(text: str) -> str:
    try:
        payload: Any = json.loads(text)
    except json.JSONDecodeError:
        if text.startswith(("{", "[")):
            return ""
        return text

    if isinstance(payload, dict) and isinstance(payload.get("answer"), str):
        return payload["answer"].strip()
    return ""
