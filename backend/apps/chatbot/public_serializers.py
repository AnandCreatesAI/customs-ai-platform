from django.conf import settings
from rest_framework import serializers


class PublicChatMessageRequestSerializer(serializers.Serializer):
    message = serializers.CharField(allow_blank=False, trim_whitespace=True)
    client_conversation_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_message(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError('Message cannot be empty.')
        max_len = int(getattr(settings, 'PUBLIC_CHAT_MAX_MESSAGE_LENGTH', 4000))
        if len(cleaned) > max_len:
            raise serializers.ValidationError(
                f'Message exceeds the maximum length of {max_len} characters.',
            )
        return cleaned
