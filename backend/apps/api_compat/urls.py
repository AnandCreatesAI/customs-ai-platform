"""Same-origin browser API paths (legacy Next BFF contract). Reuses existing DRF views."""

from django.urls import path

from apps.authentication.views import CsrfView, LoginView, LogoutView, MeView
from apps.chatbot.public_views import PublicChatMessageView
from apps.chatbot.views import ChatbotMessageView, ChatbotRegenerateView
from apps.conversations.views import (
    ConversationDetailView,
    ConversationListView,
    ConversationMessageListView,
    MessageFeedbackView,
)
from apps.documents.views import (
    DocumentDetailView,
    DocumentJsonInputView,
    DocumentListView,
    DocumentTextInputView,
    DocumentUploadView,
)
from apps.training_jobs.views import (
    TrainingJobCancelView,
    TrainingJobDetailView,
    TrainingJobListCreateView,
    TrainingJobRetryView,
)
from apps.api_compat.wrappers import wrap_view

CompatConversationDetailView = wrap_view(ConversationDetailView)
CompatConversationMessageListView = wrap_view(ConversationMessageListView)
CompatMessageFeedbackView = wrap_view(MessageFeedbackView)
CompatDocumentDetailView = wrap_view(DocumentDetailView)
CompatTrainingJobDetailView = wrap_view(TrainingJobDetailView)
CompatTrainingJobRetryView = wrap_view(TrainingJobRetryView)
CompatTrainingJobCancelView = wrap_view(TrainingJobCancelView)

urlpatterns = [
    path('auth/csrf', CsrfView.as_view(), name='compat-auth-csrf'),
    path('auth/login', LoginView.as_view(), name='compat-auth-login'),
    path('auth/logout', LogoutView.as_view(), name='compat-auth-logout'),
    path('auth/me', MeView.as_view(), name='compat-auth-me'),
    path('conversations', ConversationListView.as_view(), name='compat-conversation-list'),
    path(
        'conversations/<str:conversation_id>',
        CompatConversationDetailView.as_view(),
        name='compat-conversation-detail',
    ),
    path(
        'conversations/<str:conversation_id>/messages',
        CompatConversationMessageListView.as_view(),
        name='compat-conversation-messages',
    ),
    path(
        'conversations/messages/<str:message_id>/feedback',
        CompatMessageFeedbackView.as_view(),
        name='compat-message-feedback',
    ),
    path('chatbot/messages', ChatbotMessageView.as_view(), name='compat-chatbot-messages'),
    path('chatbot/regenerate', ChatbotRegenerateView.as_view(), name='compat-chatbot-regenerate'),
    path('public/chat/messages', PublicChatMessageView.as_view(), name='compat-public-chat-messages'),
    path('documents', DocumentListView.as_view(), name='compat-document-list'),
    path('documents/upload', DocumentUploadView.as_view(), name='compat-document-upload'),
    path('documents/text', DocumentTextInputView.as_view(), name='compat-document-text'),
    path('documents/json', DocumentJsonInputView.as_view(), name='compat-document-json'),
    path(
        'documents/<str:document_id>',
        CompatDocumentDetailView.as_view(),
        name='compat-document-detail',
    ),
    path('training/jobs', TrainingJobListCreateView.as_view(), name='compat-training-job-list'),
    path(
        'training/jobs/<str:job_id>',
        CompatTrainingJobDetailView.as_view(),
        name='compat-training-job-detail',
    ),
    path(
        'training/jobs/<str:job_id>/retry',
        CompatTrainingJobRetryView.as_view(),
        name='compat-training-job-retry',
    ),
    path(
        'training/jobs/<str:job_id>/cancel',
        CompatTrainingJobCancelView.as_view(),
        name='compat-training-job-cancel',
    ),
]
