"""
Conversation and message persistence.

Future API and service layers must scope Conversation querysets to the authenticated
user (for example, filter(user=request.user)). Conversation UUIDs are identifiers,
not authorization boundaries.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

FORBIDDEN_METADATA_KEYS = frozenset(
    {
        'api_key',
        'apikey',
        'password',
        'secret',
        'token',
        'access_token',
        'refresh_token',
        'private_key',
    }
)


class MessageRole(models.TextChoices):
    USER = 'user', 'User'
    ASSISTANT = 'assistant', 'Assistant'
    SYSTEM = 'system', 'System'


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations',
    )
    business_model = models.ForeignKey(
        'model_management.BusinessModel',
        on_delete=models.PROTECT,
        related_name='conversations',
    )
    title = models.CharField(max_length=255, blank=True, default='')
    is_pinned = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'conversation'
        verbose_name_plural = 'conversations'
        indexes = [
            models.Index(fields=['user', 'updated_at']),
            models.Index(fields=['user', 'is_pinned', 'updated_at']),
            models.Index(fields=['business_model', 'created_at']),
        ]

    def __str__(self) -> str:
        label = self.title.strip() or 'Untitled conversation'
        return f'{label} ({self.user_id})'


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(max_length=16, choices=MessageRole.choices)
    content = models.TextField()
    provider_key = models.CharField(max_length=32, blank=True)
    model_name = models.CharField(max_length=128, blank=True)
    prompt_tokens = models.PositiveIntegerField(null=True, blank=True)
    completion_tokens = models.PositiveIntegerField(null=True, blank=True)
    total_tokens = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
        verbose_name = 'message'
        verbose_name_plural = 'messages'
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['role']),
            models.Index(fields=['provider_key']),
        ]

    def __str__(self) -> str:
        preview = self.content.strip().replace('\n', ' ')[:40]
        return f'{self.role}: {preview}'

    def clean(self) -> None:
        super().clean()
        self._validate_metadata_is_non_secret(self.metadata)

    @classmethod
    def _validate_metadata_is_non_secret(cls, metadata) -> None:
        if metadata in (None, ''):
            return
        if not isinstance(metadata, dict):
            raise ValidationError({'metadata': 'Metadata must be a JSON object.'})

        def walk(value) -> None:
            if isinstance(value, dict):
                for key, nested in value.items():
                    if str(key).lower() in FORBIDDEN_METADATA_KEYS:
                        raise ValidationError(
                            {
                                'metadata': (
                                    f'Secret-like key "{key}" is not allowed in message metadata.'
                                ),
                            }
                        )
                    walk(nested)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(metadata)


class MessageFeedbackRating(models.IntegerChoices):
    UP = 1, 'Up'
    DOWN = -1, 'Down'


class MessageFeedback(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='feedback_entries',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_feedback',
    )
    rating = models.SmallIntegerField(choices=MessageFeedbackRating.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('message', 'user'),
                name='conversations_messagefeedback_message_user_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'updated_at']),
            models.Index(fields=['message']),
        ]
