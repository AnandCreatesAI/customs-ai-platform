from django.urls import path

from apps.chatbot.views import ChatbotMessageView

urlpatterns = [
    path('messages/', ChatbotMessageView.as_view(), name='chatbot-messages'),
]
