"""Production settings — load with DJANGO_SETTINGS_MODULE=config.settings.production."""

import os

from .base import *  # noqa: F403

DEBUG = False

SECRET_KEY = os.environ['SECRET_KEY']

ALLOWED_HOSTS = _split_env_list(  # noqa: F405
    'DJANGO_ALLOWED_HOSTS',
    [],
)
if not ALLOWED_HOSTS:
    raise ValueError('DJANGO_ALLOWED_HOSTS must be set in production.')

SESSION_COOKIE_SECURE = os.environ.get('DJANGO_SESSION_COOKIE_SECURE', 'true').lower() == 'true'
CSRF_COOKIE_SECURE = os.environ.get('DJANGO_CSRF_COOKIE_SECURE', 'true').lower() == 'true'

WHITENOISE_MAX_AGE = 31536000
WHITENOISE_AUTOREFRESH = False
