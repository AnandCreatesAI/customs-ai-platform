from rest_framework.settings import api_settings
from rest_framework.throttling import UserRateThrottle


class DocumentTrainingRateThrottle(UserRateThrottle):
    scope = 'document_training'

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES[self.scope]
