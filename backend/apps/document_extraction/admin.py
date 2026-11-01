from django.contrib import admin

from apps.document_extraction.models import ExtractionRun


@admin.register(ExtractionRun)
class ExtractionRunAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'document',
        'status',
        'artifact_version',
        'quality_passed',
        'created_at',
    )
    list_filter = ('status', 'business_model', 'quality_passed')
    search_fields = ('id', 'document__original_filename', 'artifact_storage_key')
    readonly_fields = ('created_at', 'completed_at', 'artifact_checksum')
