from rest_framework.settings import api_settings
from rest_framework.throttling import AnonRateThrottle


class PublicChatRateThrottle(AnonRateThrottle):
    scope = 'public_chat_message'

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES[self.scope]
