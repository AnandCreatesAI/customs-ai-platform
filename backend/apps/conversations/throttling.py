from rest_framework.settings import api_settings
from rest_framework.throttling import UserRateThrottle


class ConversationHistoryRateThrottle(UserRateThrottle):
    scope = 'conversation_history'

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES[self.scope]


class ChatbotMessageRateThrottle(UserRateThrottle):
    scope = 'chatbot_message'

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES[self.scope]
