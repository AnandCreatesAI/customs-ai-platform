from __future__ import annotations

import uuid
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.conversations.models import Conversation, Message, MessageRole
from apps.model_management.models import BusinessModel
from llm_gateway import LLMResponse

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
        message.save()
    except ValidationError as exc:
        raise MessagePersistenceError('Unable to save user message.') from exc
    return message


def persist_assistant_message(
    *,
    conversation: Conversation,
    llm_response: LLMResponse,
    provider_key: str,
    model_name: str,
) -> Message:
    metadata = _safe_message_metadata(llm_response.metadata)
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


def messages_for_conversation(conversation: Conversation):
    return conversation.messages.order_by(*MESSAGE_ORDERING)


def _safe_message_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    return {key: value for key, value in metadata.items() if key != 'request_metadata'}
