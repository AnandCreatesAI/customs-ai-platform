"""
Document metadata persistence.

Binary files are stored outside PostgreSQL; `file_path` holds the storage reference only.

Future API layers must scope Document querysets to the authenticated user
(for example, filter(user=request.user)).
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


class DocumentStatus(models.TextChoices):
    UPLOADED = 'uploaded', 'Uploaded'
    PROCESSING = 'processing', 'Processing'
    PROCESSED = 'processed', 'Processed'
    FAILED = 'failed', 'Failed'
    ARCHIVED = 'archived', 'Archived'


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents',
    )
    business_model = models.ForeignKey(
        'model_management.BusinessModel',
        on_delete=models.PROTECT,
        related_name='documents',
    )
    original_filename = models.CharField(max_length=512)
    file_type = models.CharField(max_length=128, blank=True)
    mime_type = models.CharField(max_length=128, blank=True)
    file_path = models.CharField(max_length=1024)
    file_size = models.PositiveBigIntegerField()
    checksum = models.CharField(max_length=128, blank=True, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=DocumentStatus.choices,
        default=DocumentStatus.UPLOADED,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'document'
        verbose_name_plural = 'documents'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['business_model', 'status']),
        ]

    def __str__(self) -> str:
        return f'{self.original_filename} ({self.status})'

    @staticmethod
    def normalize_file_type(value: str) -> str:
        normalized = (value or '').strip().lower()
        if normalized.startswith('.'):
            normalized = normalized[1:]
        return normalized

    @classmethod
    def file_type_from_filename(cls, filename: str) -> str:
        if not filename or '.' not in filename:
            return ''
        extension = filename.rsplit('.', 1)[-1]
        return cls.normalize_file_type(extension)

    def clean(self) -> None:
        super().clean()

        if not self.original_filename or not self.original_filename.strip():
            raise ValidationError({'original_filename': 'Original filename is required.'})

        if self.file_size is None:
            raise ValidationError({'file_size': 'File size is required.'})

        inferred_type = self.file_type_from_filename(self.original_filename)
        if self.file_type:
            self.file_type = self.normalize_file_type(self.file_type)
        else:
            self.file_type = inferred_type

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
                    if str(key).lower() in FORBIDDEN_METADATA_KEYS:
                        raise ValidationError(
                            {
                                'metadata': (
                                    f'Secret-like key "{key}" is not allowed in metadata.'
                                ),
                            }
                        )
                    walk(nested)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(metadata)
