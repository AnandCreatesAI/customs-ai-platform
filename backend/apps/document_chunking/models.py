from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.document_chunking.constants import (
    ChunkEmbeddingStatus,
    ChunkingRunStatus,
    VECTOR_DTYPE_FLOAT32,
    VECTOR_SERIALIZATION_VERSION,
)
from apps.knowledge.models import KnowledgeVisibility


class ChunkingRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    extraction_run = models.OneToOneField(
        'document_extraction.ExtractionRun',
        on_delete=models.CASCADE,
        related_name='chunking_run',
    )
    chunking_version = models.CharField(max_length=32)
    config_snapshot = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=16,
        choices=ChunkingRunStatus.choices,
        default=ChunkingRunStatus.PENDING,
        db_index=True,
    )
    chunk_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['extraction_run', 'chunking_version'],
                name='chunking_run_extraction_version_unique',
            ),
        ]
        indexes = [
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self) -> str:
        return f'ChunkingRun {self.id} ({self.status})'


class DocumentChunk(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chunking_run = models.ForeignKey(
        ChunkingRun,
        on_delete=models.CASCADE,
        related_name='chunks',
    )
    extraction_run = models.ForeignKey(
        'document_extraction.ExtractionRun',
        on_delete=models.CASCADE,
        related_name='document_chunks',
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='document_chunks',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='document_chunks',
    )
    business_model = models.ForeignKey(
        'model_management.BusinessModel',
        on_delete=models.PROTECT,
        related_name='document_chunks',
    )
    knowledge_source = models.ForeignKey(
        'knowledge.KnowledgeSource',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='document_chunks',
    )
    chunking_version = models.CharField(max_length=32)
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    content_hash = models.CharField(max_length=64, db_index=True)
    token_count = models.PositiveIntegerField()
    element_type = models.CharField(max_length=32)
    source_type = models.CharField(max_length=16)
    visibility = models.CharField(
        max_length=16,
        choices=KnowledgeVisibility.choices,
        default=KnowledgeVisibility.PRIVATE,
    )
    source_location = models.JSONField(default=dict, blank=True)
    lineage = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['extraction_run', 'chunking_version', 'chunk_index'],
                name='document_chunk_run_version_index_unique',
            ),
        ]
        indexes = [
            models.Index(fields=['document', 'created_at']),
            models.Index(fields=['business_model', 'user']),
            models.Index(fields=['content_hash']),
        ]

    def __str__(self) -> str:
        return f'Chunk {self.chunk_index} ({self.document_id})'

    def clean(self) -> None:
        super().clean()
        if self.document_id and self.user_id and self.document.user_id != self.user_id:
            raise ValidationError({'user': 'Chunk user must match document owner.'})
        if (
            self.document_id
            and self.business_model_id
            and self.document.business_model_id != self.business_model_id
        ):
            raise ValidationError({'business_model': 'Chunk business model must match document.'})


class ChunkEmbedding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document_chunk = models.ForeignKey(
        DocumentChunk,
        on_delete=models.CASCADE,
        related_name='embeddings',
    )
    embedding_model = models.CharField(max_length=128)
    embedding_model_version = models.CharField(max_length=128)
    provider_name = models.CharField(max_length=32)
    vector_kind = models.CharField(max_length=32)
    embedding_dimension = models.PositiveIntegerField()
    dtype = models.CharField(max_length=16, default=VECTOR_DTYPE_FLOAT32)
    serialization_version = models.PositiveSmallIntegerField(
        default=VECTOR_SERIALIZATION_VERSION
    )
    vector_payload = models.BinaryField()
    content_hash = models.CharField(max_length=64, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=ChunkEmbeddingStatus.choices,
        default=ChunkEmbeddingStatus.PENDING,
        db_index=True,
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['document_chunk', 'embedding_model', 'embedding_model_version'],
                name='chunk_embedding_chunk_model_unique',
            ),
        ]
        indexes = [
            models.Index(fields=['embedding_model', 'vector_kind']),
            models.Index(fields=['content_hash']),
        ]

    def __str__(self) -> str:
        return f'Embedding {self.document_chunk_id} ({self.status})'
