from __future__ import annotations

import uuid
from typing import Any

from apps.conversations.models import Conversation, Message, MessageRole
from apps.conversations.persistence import MESSAGE_ORDERING


def build_chat_context(
    *,
    conversation: Conversation,
    is_new_conversation: bool,
    user_message: str,
    history_limit: int = 20,
) -> dict[str, Any]:
    history = list(
        conversation.messages.order_by(*MESSAGE_ORDERING).values('role', 'content')[:history_limit],
    )
    prior_suggested_questions = _collect_prior_suggested_questions(conversation)
    return {
        'is_new_conversation': is_new_conversation,
        'conversation_history': history,
        'prior_suggested_questions': prior_suggested_questions,
        'latest_user_message': user_message,
        'model_key': conversation.business_model.key,
    }


def build_regenerate_context(
    *,
    conversation: Conversation,
    user_message: str,
    assistant_message_id: uuid.UUID,
    history_limit: int = 20,
) -> dict[str, Any]:
    messages = list(conversation.messages.order_by(*MESSAGE_ORDERING))
    history: list[dict[str, str]] = []
    for message in messages:
        if message.id == assistant_message_id:
            break
        history.append({'role': message.role, 'content': message.content})
    prior_suggested_questions = _collect_prior_suggested_questions(
        conversation,
        exclude_assistant_id=assistant_message_id,
    )
    return {
        'is_new_conversation': False,
        'conversation_history': history[-history_limit:],
        'prior_suggested_questions': prior_suggested_questions,
        'latest_user_message': user_message,
        'model_key': conversation.business_model.key,
        'regenerate': True,
        'regenerate_assistant_message_id': str(assistant_message_id),
    }


def _collect_prior_suggested_questions(
    conversation: Conversation,
    *,
    exclude_assistant_id: uuid.UUID | None = None,
) -> list[str]:
    queryset = conversation.messages.filter(role=MessageRole.ASSISTANT).order_by(*MESSAGE_ORDERING)
    if exclude_assistant_id is not None:
        queryset = queryset.exclude(pk=exclude_assistant_id)

    collected: list[str] = []
    seen: set[str] = set()
    for message in queryset:
        metadata = message.metadata if isinstance(message.metadata, dict) else {}
        suggestions = metadata.get('suggested_questions')
        if not isinstance(suggestions, list):
            continue
        for item in suggestions:
            if not isinstance(item, str):
                continue
            key = item.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            collected.append(item.strip())
    return collected
