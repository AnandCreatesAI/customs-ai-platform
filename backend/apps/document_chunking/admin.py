from django.contrib import admin

from apps.document_chunking.models import ChunkEmbedding, ChunkingRun, DocumentChunk


@admin.register(ChunkingRun)
class ChunkingRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'extraction_run', 'chunking_version', 'status', 'chunk_count', 'created_at')
    list_filter = ('status', 'chunking_version')
    readonly_fields = ('created_at', 'updated_at', 'started_at', 'completed_at')


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'document',
        'chunk_index',
        'element_type',
        'token_count',
        'chunking_version',
        'created_at',
    )
    list_filter = ('element_type', 'chunking_version', 'business_model')
    search_fields = ('content_hash', 'document__original_filename')
    readonly_fields = ('created_at', 'updated_at', 'content_hash')


@admin.register(ChunkEmbedding)
class ChunkEmbeddingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'document_chunk',
        'provider_name',
        'vector_kind',
        'embedding_model',
        'status',
        'embedding_dimension',
    )
    list_filter = ('provider_name', 'vector_kind', 'status')
    readonly_fields = ('created_at', 'updated_at', 'vector_payload')
