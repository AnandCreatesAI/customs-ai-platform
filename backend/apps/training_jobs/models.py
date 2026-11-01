"""
Training job orchestration metadata (all BusinessModel keys).

One Document may have many historical TrainingJob rows. Binary content stays on Document storage.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class TrainingJobStatus(models.TextChoices):
    QUEUED = 'queued', 'Queued'
    PROCESSING = 'processing', 'Processing'
    RETRYING = 'retrying', 'Retrying'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    CANCELLED = 'cancelled', 'Cancelled'


class TrainingJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='training_jobs',
    )
    business_model = models.ForeignKey(
        'model_management.BusinessModel',
        on_delete=models.PROTECT,
        related_name='training_jobs',
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='training_jobs',
    )
    parent_job = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='retry_jobs',
    )
    status = models.CharField(
        max_length=16,
        choices=TrainingJobStatus.choices,
        default=TrainingJobStatus.QUEUED,
        db_index=True,
    )
    progress = models.PositiveSmallIntegerField(default=0)
    current_stage = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    dispatch_error = models.TextField(
        blank=True,
        help_text='Broker dispatch failure; job remains queued for recovery.',
    )
    last_dispatched_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'training job'
        verbose_name_plural = 'training jobs'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['document', 'created_at']),
            models.Index(fields=['business_model', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(progress__gte=0) & Q(progress__lte=100),
                name='training_job_progress_0_100',
            ),
        ]

    def __str__(self) -> str:
        return f'TrainingJob {self.id} ({self.status})'

    def clean(self) -> None:
        super().clean()

        if self.progress < 0 or self.progress > 100:
            raise ValidationError({'progress': 'Progress must be between 0 and 100.'})

        if self.status == TrainingJobStatus.COMPLETED and self.progress != 100:
            raise ValidationError(
                {'progress': 'Completed jobs must have progress 100.'}
            )

        if self.document_id and self.user_id and self.document.user_id != self.user_id:
            raise ValidationError({'user': 'Job user must match document owner.'})

        if (
            self.document_id
            and self.business_model_id
            and self.document.business_model_id != self.business_model_id
        ):
            raise ValidationError(
                {'business_model': 'Job business model must match document business model.'}
            )
