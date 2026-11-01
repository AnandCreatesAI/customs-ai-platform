from rest_framework.settings import api_settings
from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    scope = 'auth_login'

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES[self.scope]
