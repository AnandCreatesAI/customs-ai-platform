from django.apps import AppConfig


class DocumentChunkingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.document_chunking'
    verbose_name = 'document chunking'

    def ready(self) -> None:
        from apps.document_chunking.strategies import register_default_chunk_strategies

        register_default_chunk_strategies()
