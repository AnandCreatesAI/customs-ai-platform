from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from apps.knowledge.models import (
    KnowledgeIndexingStatus,
    KnowledgeSource,
    KnowledgeSourceDocument,
    KnowledgeSourceType,
    KnowledgeVisibility,
)
from apps.training_jobs.models import TrainingJob, TrainingJobStatus


def _document_title(document) -> str:
    metadata = document.metadata or {}
    title = metadata.get('title')
    if title and str(title).strip():
        return str(title).strip()[:255]
    return document.original_filename[:255]


@transaction.atomic
def get_or_create_document_knowledge_source(*, training_job: TrainingJob) -> KnowledgeSource:
    if training_job.status != TrainingJobStatus.COMPLETED:
        raise ValidationError('KnowledgeSource provisioning requires a completed training job.')

    document = training_job.document
    if document.user_id != training_job.user_id:
        raise ValidationError('Training job user must match document owner.')
    if document.business_model_id != training_job.business_model_id:
        raise ValidationError('Training job business model must match document.')

    source, created = KnowledgeSource.objects.get_or_create(
        document=document,
        business_model=training_job.business_model,
        user=training_job.user,
        source_type=KnowledgeSourceType.DOCUMENT,
        defaults={
            'title': _document_title(document),
            'visibility': KnowledgeVisibility.PRIVATE,
            'indexing_status': KnowledgeIndexingStatus.PENDING,
        },
    )
    if not created and not source.title:
        source.title = _document_title(document)
        source.save(update_fields=['title', 'updated_at'])

    KnowledgeSourceDocument.objects.get_or_create(
        knowledge_source=source,
        document=document,
    )
    return source


def link_knowledge_source_to_document(*, knowledge_source: KnowledgeSource, document) -> None:
    if knowledge_source.business_model_id != document.business_model_id:
        raise ValidationError('KnowledgeSource business model must match document.')
    if knowledge_source.visibility == KnowledgeVisibility.PRIVATE:
        if knowledge_source.user_id != document.user_id:
            raise ValidationError('Private KnowledgeSource owner must match document owner.')
    elif knowledge_source.user_id != document.user_id:
        raise ValidationError(
            'Shared KnowledgeSource cannot be linked to another user\'s document '
            'without an organization-level entitlement policy (not defined in this project).'
        )
    KnowledgeSourceDocument.objects.get_or_create(
        knowledge_source=knowledge_source,
        document=document,
    )


def knowledge_sources_for_document(*, document_id, business_model_id):
    return (
        KnowledgeSource.objects.filter(business_model_id=business_model_id)
        .filter(
            Q(document_links__document_id=document_id)
            | Q(document_id=document_id, source_type=KnowledgeSourceType.DOCUMENT)
        )
        .distinct()
    )
