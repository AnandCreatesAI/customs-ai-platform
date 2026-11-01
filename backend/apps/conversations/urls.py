from django.urls import path

from apps.conversations.views import (
    ConversationDetailView,
    ConversationListView,
    ConversationMessageListView,
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
]
