from __future__ import annotations

import uuid
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.conversations.models import Conversation, Message, MessageRole
from apps.conversations.titles import (
    is_legacy_deterministic_title,
    is_placeholder_conversation_title,
    truncate_plain_title,
)
from apps.model_management.models import BusinessModel
from gateways.llm import LLMResponse

MESSAGE_ORDERING = ('created_at', 'id')


class ConversationAccessError(Exception):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class MessagePersistenceError(Exception):
    """Raised when a message row cannot be validated or saved."""


def get_conversation_for_access(
    *,
    user,
    conversation_id: uuid.UUID,
    require_active: bool = True,
) -> Conversation:
    try:
        conversation = Conversation.objects.select_related('business_model').get(
            pk=conversation_id,
            user=user,
        )
    except Conversation.DoesNotExist as exc:
        raise ConversationAccessError(
            'Conversation not found.',
            status_code=404,
        ) from exc

    if require_active and not conversation.is_active:
        raise ConversationAccessError(
            'Conversation is inactive.',
            status_code=400,
        )
    return conversation


def resolve_conversation(
    *,
    user,
    business_model: BusinessModel,
    conversation_id: uuid.UUID | None,
    lock: bool = False,
) -> tuple[Conversation, bool]:
    """
    Return (conversation, created). When conversation_id is omitted, create a new row.
    When lock=True and continuing an existing conversation, take a row lock for the
    duration of the surrounding transaction (must not span external LLM calls).
    """
    if conversation_id is None:
        conversation = Conversation.objects.create(
            user=user,
            business_model=business_model,
        )
        return conversation, True

    queryset = Conversation.objects.filter(pk=conversation_id, user=user)
    if lock:
        queryset = queryset.select_for_update()
    try:
        conversation = queryset.get()
    except Conversation.DoesNotExist as exc:
        raise ConversationAccessError(
            'Conversation not found.',
            status_code=404,
        ) from exc

    if conversation.business_model_id != business_model.id:
        raise ConversationAccessError(
            'Conversation does not match the selected business model.',
            status_code=400,
        )
    if not conversation.is_active:
        raise ConversationAccessError(
            'Conversation is inactive.',
            status_code=400,
        )
    return conversation, False


def persist_user_message(*, conversation: Conversation, content: str) -> Message:
    message = Message(
        conversation=conversation,
        role=MessageRole.USER,
        content=content,
    )
    try:
        message.full_clean()
        with transaction.atomic():
            message.save()
    except ValidationError as exc:
        raise MessagePersistenceError('Unable to save user message.') from exc
    return message


def apply_llm_conversation_title(
    conversation: Conversation,
    title: str | None,
    *,
    user_message_fallback: str,
) -> None:
    if not is_placeholder_conversation_title(conversation.title):
        return

    generated = (title or '').strip()
    if not generated or is_placeholder_conversation_title(generated):
        generated = truncate_plain_title(user_message_fallback)
    if not generated or is_placeholder_conversation_title(generated):
        return

    Conversation.objects.filter(pk=conversation.pk).update(title=generated)
    conversation.title = generated


def backfill_conversation_title(conversation: Conversation) -> bool:
    """
    When a legacy row still has a placeholder title, derive one from the first
    persisted user message and save it. Returns True when the row was updated.
    """
    if not is_placeholder_conversation_title(conversation.title):
        return False

    first_user = (
        conversation.messages.filter(role=MessageRole.USER)
        .order_by(*MESSAGE_ORDERING)
        .only('content')
        .first()
    )
    if not first_user:
        return False

    generated = truncate_plain_title(first_user.content)
    if not generated or is_placeholder_conversation_title(generated):
        return False

    Conversation.objects.filter(pk=conversation.pk).update(title=generated)
    conversation.title = generated
    return True


def refresh_legacy_deterministic_title(conversation: Conversation) -> bool:
    """
    Replace auto-generated "Understanding …" titles that match the legacy deterministic
    algorithm with a plain-language excerpt from the first user message.
    """
    if is_placeholder_conversation_title(conversation.title):
        return False

    first_user = (
        conversation.messages.filter(role=MessageRole.USER)
        .order_by(*MESSAGE_ORDERING)
        .only('content')
        .first()
    )
    if not first_user:
        return False

    if not is_legacy_deterministic_title(conversation.title, first_user.content):
        return False

    replacement = truncate_plain_title(first_user.content)
    if not replacement or is_placeholder_conversation_title(replacement):
        return False
    if replacement.strip() == conversation.title.strip():
        return False

    Conversation.objects.filter(pk=conversation.pk).update(title=replacement)
    conversation.title = replacement
    return True


def conversations_for_recent_chats(user):
    return (
        Conversation.objects.filter(user=user, is_active=True)
        .filter(messages__role=MessageRole.USER)
        .distinct()
        .select_related('business_model')
        .order_by('-is_pinned', '-updated_at', '-id')
    )


def persist_assistant_message(
    *,
    conversation: Conversation,
    llm_response: LLMResponse,
    provider_key: str,
    model_name: str,
) -> Message:
    metadata = _assistant_metadata_from_response(llm_response)
    message = Message(
        conversation=conversation,
        role=MessageRole.ASSISTANT,
        content=llm_response.content,
        provider_key=provider_key,
        model_name=model_name,
        metadata=metadata,
    )
    try:
        message.full_clean()
    except ValidationError as exc:
        raise MessagePersistenceError('Unable to save assistant message.') from exc

    try:
        with transaction.atomic():
            message.save()
            Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())
    except ValidationError as exc:
        raise MessagePersistenceError('Unable to save assistant message.') from exc
    return message


def regenerate_assistant_message(
    *,
    assistant_message: Message,
    llm_response: LLMResponse,
    provider_key: str,
    model_name: str,
) -> Message:
    metadata = _assistant_metadata_from_response(llm_response)
    assistant_message.content = llm_response.content
    assistant_message.provider_key = provider_key
    assistant_message.model_name = model_name
    assistant_message.metadata = metadata
    try:
        assistant_message.full_clean()
    except ValidationError as exc:
        raise MessagePersistenceError('Unable to save assistant message.') from exc

    try:
        with transaction.atomic():
            assistant_message.save(
                update_fields=[
                    'content',
                    'provider_key',
                    'model_name',
                    'metadata',
                ],
            )
            Conversation.objects.filter(pk=assistant_message.conversation_id).update(
                updated_at=timezone.now(),
            )
    except ValidationError as exc:
        raise MessagePersistenceError('Unable to save assistant message.') from exc
    return assistant_message


def messages_for_conversation(conversation: Conversation):
    return conversation.messages.order_by(*MESSAGE_ORDERING)


def _assistant_metadata_from_response(llm_response: LLMResponse) -> dict[str, Any]:
    metadata = _safe_message_metadata(llm_response.metadata)
    suggestions = metadata.pop('suggested_questions', None)
    if isinstance(suggestions, list):
        cleaned = [item for item in suggestions if isinstance(item, str) and item.strip()]
        metadata['suggested_questions'] = cleaned[:3]
    else:
        metadata.setdefault('suggested_questions', [])

    metadata.pop('conversation_title', None)
    metadata.pop('provider', None)
    metadata.pop('model', None)

    _normalize_rag_metadata(metadata)
    return metadata


def _normalize_rag_metadata(metadata: dict[str, Any]) -> None:
    sources = metadata.get('sources')
    if sources is not None and not isinstance(sources, list):
        metadata.pop('sources', None)

    if 'sources' in metadata:
        sanitized: list[dict[str, Any]] = []
        for item in metadata['sources']:
            if not isinstance(item, dict):
                continue
            entry = {
                key: item[key]
                for key in (
                    'ref',
                    'chunk_id',
                    'document_id',
                    'document_filename',
                    'chunk_index',
                    'score',
                    'artifact_version',
                )
                if key in item
            }
            if 'ref' in entry and 'chunk_id' in entry and 'document_id' in entry:
                sanitized.append(entry)
        metadata['sources'] = sanitized

    evidence_detail = metadata.get('evidence_detail')
    if evidence_detail is not None and not isinstance(evidence_detail, dict):
        metadata.pop('evidence_detail', None)

    rag_retrieval = metadata.get('rag_retrieval')
    if rag_retrieval is not None and not isinstance(rag_retrieval, dict):
        metadata.pop('rag_retrieval', None)


def _safe_message_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    return {key: value for key, value in metadata.items() if key != 'request_metadata'}
