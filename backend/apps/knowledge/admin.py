from django.contrib import admin

from apps.knowledge.models import KnowledgeSource, KnowledgeSourceDocument


@admin.register(KnowledgeSource)
class KnowledgeSourceAdmin(admin.ModelAdmin):
    ordering = ('-created_at',)
    list_display = (
        'title',
        'user',
        'business_model',
        'source_type',
        'visibility',
        'indexing_status',
        'created_at',
    )
    list_filter = (
        'business_model',
        'source_type',
        'visibility',
        'indexing_status',
    )
    search_fields = ('title', 'user__email', 'vector_store')
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        (
            None,
            {
                'fields': (
                    'id',
                    'title',
                    'source_type',
                    'visibility',
                    'user',
                    'business_model',
                    'document',
                ),
            },
        ),
        (
            'Indexing',
            {
                'fields': ('indexing_status', 'vector_store'),
                'description': (
                    'vector_store holds an external vector reference only; embeddings are not stored in PostgreSQL.'
                ),
            },
        ),
        ('Metadata', {'fields': ('metadata',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
