from django.urls import path

from apps.conversations.views import (
    ConversationDetailView,
    ConversationListView,
    ConversationMessageListView,
    MessageFeedbackView,
)

urlpatterns = [
    path('', ConversationListView.as_view(), name='conversation-list'),
    path(
        '<uuid:conversation_id>/',
        ConversationDetailView.as_view(),
        name='conversation-detail',
    ),
    path(
        '<uuid:conversation_id>/messages/',
        ConversationMessageListView.as_view(),
        name='conversation-messages',
    ),
    path(
        'messages/<uuid:message_id>/feedback/',
        MessageFeedbackView.as_view(),
        name='message-feedback',
    ),
]
