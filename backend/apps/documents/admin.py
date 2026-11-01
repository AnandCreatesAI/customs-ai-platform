from django.contrib import admin

from apps.documents.models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    ordering = ('-created_at',)
    list_display = (
        'original_filename',
        'user',
        'business_model',
        'file_type',
        'status',
        'file_size',
        'created_at',
    )
    list_filter = ('business_model', 'status', 'file_type')
    search_fields = ('original_filename', 'user__email', 'file_path', 'checksum')
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        (
            None,
            {
                'fields': (
                    'id',
                    'user',
                    'business_model',
                    'original_filename',
                    'file_type',
                    'mime_type',
                    'status',
                ),
            },
        ),
        (
            'Storage reference',
            {
                'fields': ('file_path', 'file_size', 'checksum'),
                'description': 'Binary content is stored outside the database. file_path is a storage reference only.',
            },
        ),
        ('Metadata', {'fields': ('metadata',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
