from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from apps.conversations.titles import (
    is_placeholder_conversation_title,
    truncate_plain_title,
)

_GENERIC_LLM_TITLES = frozenset(
    {
        'chat',
        'custom',
        'help',
        'new chat',
        'new conversation',
        'question',
        'understanding chat',
        'general question',
    }
)

_MAX_SUGGESTED_QUESTIONS = 3
_MAX_TITLE_LENGTH = 255


@dataclass(frozen=True)
class ParsedStructuredChatResponse:
    answer: str
    conversation_title: str | None
    suggested_questions: list[str]


def structured_output_system_addon(context: dict[str, Any]) -> str:
    is_new = bool(context.get('is_new_conversation'))
    prior_questions = context.get('prior_suggested_questions') or []
    history = context.get('conversation_history') or []

    history_lines: list[str] = []
    for entry in history[-12:]:
        role = entry.get('role', 'user')
        content = str(entry.get('content', '')).strip()
        if content:
            history_lines.append(f'{role.upper()}: {content[:800]}')

    prior_block = ''
    if prior_questions:
        prior_block = (
            '\nDo not repeat or closely paraphrase these prior suggested questions:\n'
            + '\n'.join(f'- {q}' for q in prior_questions[:24])
        )

    title_rule = (
        'Include conversation_title: a concise professional title (3–7 words) describing '
        'the user intent for this new conversation. Use specific noun phrases; do not '
        'start titles with "Understanding" or other generic teaching prefixes.'
        if is_new
        else 'Set conversation_title to null (existing conversation).'
    )

    return (
        '\n\n--- Response format (mandatory) ---\n'
        'Return exactly one JSON object with no surrounding markdown or commentary.\n'
        'Schema:\n'
        '{\n'
        '  "answer": "markdown string shown to the user",\n'
        '  "conversation_title": string or null,\n'
        '  "suggested_questions": ["up to three short follow-up questions"]\n'
        '}\n'
        f'{title_rule}\n'
        'suggested_questions must be relevant to the latest exchange, the selected business '
        'model domain, and useful next steps. Omit weak duplicates. Return fewer than three '
        'if fewer strong questions exist.\n'
        f'{prior_block}\n'
        + (
            'Recent conversation context:\n' + '\n'.join(history_lines) + '\n'
            if history_lines
            else ''
        )
    )


def parse_structured_chat_response(
    raw_content: str,
    *,
    is_new_conversation: bool,
    user_message_for_title_fallback: str,
    rag_enabled: bool = False,
) -> ParsedStructuredChatResponse:
    payload = _load_json_object(raw_content)
    if payload is None:
        if rag_enabled:
            from apps.rag.exceptions import RagStructuredOutputError

            raise RagStructuredOutputError()
        return ParsedStructuredChatResponse(
            answer=raw_content.strip(),
            conversation_title=_safe_fallback_title(user_message_for_title_fallback)
            if is_new_conversation
            else None,
            suggested_questions=[],
        )

    answer = _coerce_non_empty_string(payload.get('answer'))
    if not answer:
        if rag_enabled:
            from apps.rag.exceptions import RagStructuredOutputError

            raise RagStructuredOutputError()
        answer = raw_content.strip()
    title = _normalize_llm_title(payload.get('conversation_title'))
    if is_new_conversation and not title:
        title = _safe_fallback_title(user_message_for_title_fallback)

    suggestions = _normalize_suggested_questions(payload.get('suggested_questions'))

    return ParsedStructuredChatResponse(
        answer=answer,
        conversation_title=title if is_new_conversation else None,
        suggested_questions=suggestions,
    )


def _load_json_object(raw_content: str) -> dict[str, Any] | None:
    text = raw_content.strip()
    if not text:
        return None

    fence_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()

    if not text.startswith('{'):
        start = text.find('{')
        end = text.rfind('}')
        if start >= 0 and end > start:
            text = text[start : end + 1]

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _coerce_non_empty_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_llm_title(value: Any) -> str | None:
    title = _coerce_non_empty_string(value)
    if not title:
        return None
    title = re.sub(r'\s+', ' ', title).strip()
    if len(title) > _MAX_TITLE_LENGTH:
        title = title[: _MAX_TITLE_LENGTH - 1].rstrip() + '…'
    if is_placeholder_conversation_title(title):
        return None
    if title.lower() in _GENERIC_LLM_TITLES:
        return None
    if title.lower().startswith('understanding '):
        return None
    return title


def _normalize_suggested_questions(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    results: list[str] = []
    seen: set[str] = set()
    for item in value:
        question = _coerce_non_empty_string(item)
        if not question:
            continue
        question = question.rstrip('?.! ').strip() + '?'
        key = question.lower()
        if key in seen:
            continue
        seen.add(key)
        results.append(question)
        if len(results) >= _MAX_SUGGESTED_QUESTIONS:
            break
    return results


def _safe_fallback_title(user_message: str) -> str | None:
    fallback = truncate_plain_title(user_message, max_length=_MAX_TITLE_LENGTH)
    if not fallback or is_placeholder_conversation_title(fallback):
        return None
    if fallback.lower() in _GENERIC_LLM_TITLES:
        return None
    return fallback
