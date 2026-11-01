from rest_framework.settings import api_settings
from rest_framework.throttling import UserRateThrottle


class TrainingJobRateThrottle(UserRateThrottle):
    scope = 'training_jobs'

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES[self.scope]
