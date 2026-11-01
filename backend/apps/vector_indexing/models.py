from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.vector_indexing.constants import (
    ChunkVectorIndexStatus,
    IndexingActivationPhase,
    IndexingRunStatus,
)


class IndexingRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    training_job = models.ForeignKey(
        'training_jobs.TrainingJob',
        on_delete=models.CASCADE,
        related_name='indexing_runs',
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='indexing_runs',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='indexing_runs',
    )
    business_model = models.ForeignKey(
        'model_management.BusinessModel',
        on_delete=models.PROTECT,
        related_name='indexing_runs',
    )
    extraction_run = models.ForeignKey(
        'document_extraction.ExtractionRun',
        on_delete=models.CASCADE,
        related_name='indexing_runs',
    )
    chunking_run = models.ForeignKey(
        'document_chunking.ChunkingRun',
        on_delete=models.CASCADE,
        related_name='indexing_runs',
    )
    artifact_version = models.PositiveIntegerField()
    embedding_dimension = models.PositiveIntegerField()
    embedding_model = models.CharField(max_length=128, blank=True)
    embedding_model_version = models.CharField(max_length=128, blank=True)
    collection_name = models.CharField(max_length=256, blank=True)
    status = models.CharField(
        max_length=16,
        choices=IndexingRunStatus.choices,
        default=IndexingRunStatus.QUEUED,
        db_index=True,
    )
    total_chunks = models.PositiveIntegerField(default=0)
    indexed_chunks = models.PositiveIntegerField(default=0)
    failed_chunks = models.PositiveIntegerField(default=0)
    retry_count = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True)
    skip_reason = models.CharField(max_length=128, blank=True)
    dispatch_error = models.TextField(blank=True)
    activation_reconciled = models.BooleanField(default=False)
    activation_phase = models.CharField(
        max_length=32,
        choices=IndexingActivationPhase.choices,
        default=IndexingActivationPhase.NONE,
        db_index=True,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['document', 'business_model']),
            models.Index(fields=['training_job', 'created_at']),
            models.Index(fields=['chunking_run', 'embedding_dimension', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'chunking_run',
                    'embedding_dimension',
                    'embedding_model',
                    'embedding_model_version',
                ],
                condition=models.Q(status=IndexingRunStatus.COMPLETED),
                name='indexing_run_success_per_embedding_config',
            ),
            models.UniqueConstraint(
                fields=[
                    'chunking_run',
                    'embedding_dimension',
                    'embedding_model',
                    'embedding_model_version',
                ],
                condition=models.Q(
                    status__in=[
                        IndexingRunStatus.QUEUED,
                        IndexingRunStatus.PROCESSING,
                        IndexingRunStatus.RETRYING,
                    ]
                ),
                name='indexing_run_active_per_embedding_config',
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.document_id and self.user_id and self.document.user_id != self.user_id:
            raise ValidationError({'user': 'Indexing run user must match document owner.'})
        if (
            self.document_id
            and self.business_model_id
            and self.document.business_model_id != self.business_model_id
        ):
            raise ValidationError({'business_model': 'Indexing run business model mismatch.'})


class ChunkVectorIndex(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    indexing_run = models.ForeignKey(
        IndexingRun,
        on_delete=models.CASCADE,
        related_name='chunk_indexes',
    )
    document_chunk = models.ForeignKey(
        'document_chunking.DocumentChunk',
        on_delete=models.CASCADE,
        related_name='vector_indexes',
    )
    chunk_embedding = models.ForeignKey(
        'document_chunking.ChunkEmbedding',
        on_delete=models.CASCADE,
        related_name='vector_indexes',
    )
    qdrant_point_id = models.UUIDField()
    collection_name = models.CharField(max_length=256)
    embedding_dimension = models.PositiveIntegerField()
    status = models.CharField(
        max_length=16,
        choices=ChunkVectorIndexStatus.choices,
        default=ChunkVectorIndexStatus.PENDING,
        db_index=True,
    )
    error_message = models.TextField(blank=True)
    indexed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['indexing_run', 'chunk_embedding'],
                name='chunk_vector_index_run_embedding_unique',
            ),
        ]
        indexes = [
            models.Index(fields=['qdrant_point_id']),
            models.Index(fields=['collection_name', 'status']),
        ]


class DocumentIndexActivation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='index_activations',
    )
    business_model = models.ForeignKey(
        'model_management.BusinessModel',
        on_delete=models.PROTECT,
        related_name='index_activations',
    )
    active_artifact_version = models.PositiveIntegerField()
    active_indexing_run = models.ForeignKey(
        IndexingRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activations',
    )
    active_collection_name = models.CharField(max_length=256, blank=True)
    pending_indexing_run = models.ForeignKey(
        IndexingRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pending_activations',
    )
    pending_artifact_version = models.PositiveIntegerField(null=True, blank=True)
    pending_collection_name = models.CharField(max_length=256, blank=True)
    pending_since = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['document', 'business_model'],
                name='document_index_activation_unique',
            ),
        ]
