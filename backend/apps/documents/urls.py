from django.urls import path

from apps.documents.views import (
    DocumentDetailView,
    DocumentJsonInputView,
    DocumentListView,
    DocumentTextInputView,
    DocumentUploadView,
)

urlpatterns = [
    path('', DocumentListView.as_view(), name='document-list'),
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('text/', DocumentTextInputView.as_view(), name='document-text'),
    path('json/', DocumentJsonInputView.as_view(), name='document-json'),
    path('<uuid:document_id>/', DocumentDetailView.as_view(), name='document-detail'),
]
