from django.apps import AppConfig


class ApiCompatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.api_compat'
    verbose_name = 'Browser API compatibility routes'
