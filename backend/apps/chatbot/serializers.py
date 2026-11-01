from rest_framework import serializers

from apps.model_management.models import BusinessModel
from model_handlers.registry import MODEL_HANDLER_CLASSES


class ChatbotMessageRequestSerializer(serializers.Serializer):
    model_key = serializers.ChoiceField(choices=sorted(MODEL_HANDLER_CLASSES.keys()))
    message = serializers.CharField(allow_blank=False, trim_whitespace=True)
    conversation_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_message(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError('Message cannot be empty.')
        return value.strip()

    def validate_model_key(self, value: str) -> str:
        try:
            business_model = BusinessModel.objects.get(key=value)
        except BusinessModel.DoesNotExist:
            raise serializers.ValidationError('Business model is not configured.') from None
        if not business_model.is_active:
            raise serializers.ValidationError('Business model is inactive.')
        return value

    @property
    def business_model(self) -> BusinessModel:
        return BusinessModel.objects.get(key=self.validated_data['model_key'])
