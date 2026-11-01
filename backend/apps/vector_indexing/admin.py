from django.contrib import admin

from apps.vector_indexing.models import ChunkVectorIndex, DocumentIndexActivation, IndexingRun


@admin.register(IndexingRun)
class IndexingRunAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'document',
        'business_model',
        'status',
        'collection_name',
        'indexed_chunks',
        'total_chunks',
        'created_at',
    )
    list_filter = ('status', 'business_model')
    readonly_fields = ('created_at', 'updated_at', 'started_at', 'completed_at')


@admin.register(ChunkVectorIndex)
class ChunkVectorIndexAdmin(admin.ModelAdmin):
    list_display = ('id', 'indexing_run', 'qdrant_point_id', 'status', 'collection_name')
    list_filter = ('status',)


@admin.register(DocumentIndexActivation)
class DocumentIndexActivationAdmin(admin.ModelAdmin):
    list_display = (
        'document',
        'business_model',
        'active_artifact_version',
        'active_collection_name',
        'activated_at',
    )
