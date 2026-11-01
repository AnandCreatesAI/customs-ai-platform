"""
Knowledge source metadata for future indexing and retrieval.

Embeddings and vector payloads are stored outside PostgreSQL. Linking a Document does
not grant document access; future authorization must enforce document and knowledge
rules independently.
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
        'embedding',
        'embeddings',
        'vector',
        'vectors',
    }
)


class KnowledgeSourceType(models.TextChoices):
    DOCUMENT = 'document', 'Document'
    TEXT = 'text', 'Text'
    URL = 'url', 'URL'
    MANUAL = 'manual', 'Manual'


class KnowledgeVisibility(models.TextChoices):
    SHARED = 'shared', 'Shared'
    PRIVATE = 'private', 'Private'


class KnowledgeIndexingStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    INDEXED = 'indexed', 'Indexed'
    FAILED = 'failed', 'Failed'


class KnowledgeSource(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='knowledge_sources',
    )
    business_model = models.ForeignKey(
        'model_management.BusinessModel',
        on_delete=models.PROTECT,
        related_name='knowledge_sources',
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='knowledge_sources',
    )
    source_type = models.CharField(max_length=16, choices=KnowledgeSourceType.choices)
    title = models.CharField(max_length=255)
    visibility = models.CharField(
        max_length=16,
        choices=KnowledgeVisibility.choices,
        default=KnowledgeVisibility.PRIVATE,
    )
    indexing_status = models.CharField(
        max_length=16,
        choices=KnowledgeIndexingStatus.choices,
        default=KnowledgeIndexingStatus.PENDING,
    )
    vector_store = models.CharField(max_length=512, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'knowledge source'
        verbose_name_plural = 'knowledge sources'
        indexes = [
            models.Index(fields=['business_model', 'visibility', 'indexing_status']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['document']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(visibility=KnowledgeVisibility.SHARED)
                    | models.Q(user__isnull=False)
                ),
                name='knowledge_private_requires_owner',
            ),
            models.UniqueConstraint(
                fields=['document', 'business_model', 'user', 'source_type'],
                condition=models.Q(
                    document__isnull=False,
                    source_type=KnowledgeSourceType.DOCUMENT,
                ),
                name='knowledge_unique_document_source_per_owner',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.title} ({self.source_type})'

    def clean(self) -> None:
        super().clean()

        if not self.title or not self.title.strip():
            raise ValidationError({'title': 'Title is required.'})

        if self.visibility == KnowledgeVisibility.PRIVATE and self.user is None:
            raise ValidationError({'user': 'Private knowledge sources must have an owner.'})

        self._validate_metadata(self.metadata)

    @classmethod
    def _validate_metadata(cls, metadata) -> None:
        if metadata in (None, ''):
            return
        if not isinstance(metadata, dict):
            raise ValidationError({'metadata': 'Metadata must be a JSON object.'})

        def walk(value) -> None:
            if isinstance(value, dict):
                for key, nested in value.items():
                    key_lower = str(key).lower()
                    if key_lower in FORBIDDEN_METADATA_KEYS:
                        raise ValidationError(
                            {
                                'metadata': (
                                    f'Key "{key}" is not allowed in knowledge metadata.'
                                ),
                            }
                        )
                    walk(nested)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(metadata)


class KnowledgeSourceDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    knowledge_source = models.ForeignKey(
        KnowledgeSource,
        on_delete=models.CASCADE,
        related_name='document_links',
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='knowledge_source_links',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['knowledge_source', 'document'],
                name='knowledge_source_document_unique',
            ),
        ]
        indexes = [
            models.Index(fields=['document']),
        ]

    def clean(self) -> None:
        super().clean()
        source = self.knowledge_source
        document = self.document
        if source.business_model_id != document.business_model_id:
            raise ValidationError(
                {'document': 'Document business model must match KnowledgeSource.'}
            )
        if source.visibility == KnowledgeVisibility.PRIVATE and source.user_id != document.user_id:
            raise ValidationError(
                {'document': 'Private KnowledgeSource owner must match document owner.'}
            )
        if source.visibility == KnowledgeVisibility.SHARED and source.user_id != document.user_id:
            raise ValidationError(
                {
                    'document': (
                        'Shared KnowledgeSource cannot link to another user\'s document '
                        'without organization-level entitlement (not defined).'
                    )
                }
            )
