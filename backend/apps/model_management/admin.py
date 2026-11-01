from django.contrib import admin

from apps.model_management.models import BusinessModel, LLMProviderProfile


@admin.register(BusinessModel)
class BusinessModelAdmin(admin.ModelAdmin):
    ordering = ('key',)
    list_display = ('key', 'name', 'is_active', 'updated_at')
    list_filter = ('is_active', 'key')
    search_fields = ('key', 'name', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('key', 'name', 'description', 'is_active')}),
        ('Metadata', {'fields': ('id', 'created_at', 'updated_at')}),
    )


@admin.register(LLMProviderProfile)
class LLMProviderProfileAdmin(admin.ModelAdmin):
    ordering = ('provider_key',)
    list_display = (
        'provider_key',
        'display_name',
        'model_name',
        'api_key_env_var',
        'is_active',
        'updated_at',
    )
    list_filter = ('is_active',)
    search_fields = ('provider_key', 'display_name', 'model_name', 'api_key_env_var')
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        (
            None,
            {
                'fields': (
                    'provider_key',
                    'display_name',
                    'model_name',
                    'api_key_env_var',
                    'is_active',
                ),
            },
        ),
        (
            'Non-secret configuration',
            {
                'fields': ('configuration',),
                'description': (
                    'Store only non-sensitive provider settings. API keys must remain in '
                    'environment variables referenced by api_key_env_var.'
                ),
            },
        ),
        ('Metadata', {'fields': ('id', 'created_at', 'updated_at')}),
    )
