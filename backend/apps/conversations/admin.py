from django.contrib import admin

from apps.conversations.models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('id', 'role', 'provider_key', 'model_name', 'created_at')
    fields = (
        'id',
        'role',
        'content',
        'provider_key',
        'model_name',
        'prompt_tokens',
        'completion_tokens',
        'total_tokens',
        'metadata',
        'created_at',
    )


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    ordering = ('-created_at',)
    list_display = ('title', 'user', 'business_model', 'is_active', 'created_at')
    list_filter = ('is_active', 'business_model')
    search_fields = ('title', 'user__email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = (MessageInline,)
    fieldsets = (
        (None, {'fields': ('id', 'user', 'business_model', 'title', 'is_active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    ordering = ('-created_at',)
    list_display = ('conversation', 'role', 'provider_key', 'model_name', 'created_at')
    list_filter = ('role', 'provider_key')
    search_fields = ('content', 'conversation__title', 'conversation__user__email')
    readonly_fields = ('id', 'created_at')
    fieldsets = (
        (
            None,
            {
                'fields': (
                    'id',
                    'conversation',
                    'role',
                    'content',
                    'provider_key',
                    'model_name',
                ),
            },
        ),
        (
            'Usage',
            {'fields': ('prompt_tokens', 'completion_tokens', 'total_tokens', 'metadata')},
        ),
        ('Timestamps', {'fields': ('created_at',)}),
    )
