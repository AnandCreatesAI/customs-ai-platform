from django.apps import AppConfig


class DocumentExtractionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.document_extraction'
    verbose_name = 'document extraction'

    def ready(self) -> None:
        import apps.document_extraction.extractors  # noqa: F401 — register extractors
