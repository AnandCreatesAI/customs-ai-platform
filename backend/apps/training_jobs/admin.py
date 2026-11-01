from django.contrib import admin

from apps.training_jobs.models import TrainingJob


@admin.register(TrainingJob)
class TrainingJobAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'business_model',
        'document',
        'status',
        'progress',
        'retry_count',
        'created_at',
    )
    list_filter = ('status', 'business_model')
    search_fields = ('id', 'document__original_filename', 'user__email')
    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
        'started_at',
        'completed_at',
        'last_dispatched_at',
        'dispatch_error',
    )
