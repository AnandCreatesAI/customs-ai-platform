from django.urls import path

from apps.chatbot.public_views import PublicChatMessageView
from apps.chatbot.views import ChatbotMessageView, ChatbotRegenerateView

urlpatterns = [
    path('messages/', ChatbotMessageView.as_view(), name='chatbot-messages'),
    path('regenerate/', ChatbotRegenerateView.as_view(), name='chatbot-regenerate'),
    path('public/messages/', PublicChatMessageView.as_view(), name='chatbot-public-messages'),
]
