from rest_framework import serializers

from apps.conversations.models import Conversation, Message


class ConversationSummarySerializer(serializers.ModelSerializer):
    model_key = serializers.CharField(source='business_model.key', read_only=True)

    class Meta:
        model = Conversation
        fields = (
            'id',
            'title',
            'model_key',
            'is_active',
            'created_at',
            'updated_at',
        )


class MessageHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = (
            'id',
            'role',
            'content',
            'provider_key',
            'model_name',
            'created_at',
        )


class ConversationDetailSerializer(serializers.ModelSerializer):
    model_key = serializers.CharField(source='business_model.key', read_only=True)

    class Meta:
        model = Conversation
        fields = (
            'id',
            'title',
            'model_key',
            'is_active',
            'created_at',
            'updated_at',
        )
