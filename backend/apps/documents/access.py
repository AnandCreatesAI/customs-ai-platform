from django.shortcuts import get_object_or_404

from apps.documents.models import Document


def documents_for_user(user):
    return Document.objects.filter(user=user).select_related('business_model')


def get_document_for_user(user, document_id):
    return get_object_or_404(documents_for_user(user), id=document_id)
