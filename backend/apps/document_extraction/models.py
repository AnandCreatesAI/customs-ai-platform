from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ExtractionRunStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    RUNNING = 'running', 'Running'
    SUCCEEDED = 'succeeded', 'Succeeded'
    FAILED = 'failed', 'Failed'


class ExtractionRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    training_job = models.OneToOneField(
        'training_jobs.TrainingJob',
        on_delete=models.CASCADE,
        related_name='extraction_run',
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='extraction_runs',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='extraction_runs',
    )
    business_model = models.ForeignKey(
        'model_management.BusinessModel',
        on_delete=models.PROTECT,
        related_name='extraction_runs',
    )
    status = models.CharField(
        max_length=16,
        choices=ExtractionRunStatus.choices,
        default=ExtractionRunStatus.PENDING,
        db_index=True,
    )
    schema_version = models.CharField(max_length=16)
    extractor_key = models.CharField(max_length=32, blank=True)
    artifact_version = models.PositiveIntegerField()
    artifact_storage_key = models.CharField(max_length=1024, blank=True)
    artifact_checksum = models.CharField(max_length=128, blank=True)
    artifact_byte_size = models.PositiveBigIntegerField(default=0)
    quality_passed = models.BooleanField(default=False)
    meaningful_content = models.BooleanField(default=False)
    summary = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['document', 'artifact_version'],
                name='extraction_run_document_version_unique',
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['business_model', 'status']),
        ]

    def clean(self) -> None:
        super().clean()
        if self.document_id and self.user_id and self.document.user_id != self.user_id:
            raise ValidationError({'user': 'Extraction run user must match document owner.'})
        if (
            self.document_id
            and self.business_model_id
            and self.document.business_model_id != self.business_model_id
        ):
            raise ValidationError(
                {'business_model': 'Extraction run business model must match document.'}
            )
