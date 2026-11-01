from rest_framework import serializers

from model_handlers.registry import MODEL_HANDLER_CLASSES


class SemanticRetrievalRequestSerializer(serializers.Serializer):
    business_model = serializers.ChoiceField(choices=sorted(MODEL_HANDLER_CLASSES.keys()))
    query = serializers.CharField(allow_blank=False, trim_whitespace=True)
    top_k = serializers.IntegerField(required=False, min_value=1)
    min_score = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    document_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=False,
    )

    def validate_query(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError('Query cannot be empty.')
        return value.strip()


class RetrievalResultItemSerializer(serializers.Serializer):
    chunk_id = serializers.UUIDField()
    document_id = serializers.UUIDField()
    score = serializers.FloatField()
    chunk_index = serializers.IntegerField()
    content = serializers.CharField()
    element_type = serializers.CharField()
    source_type = serializers.CharField()
    artifact_version = serializers.IntegerField()
    content_hash = serializers.CharField()
    truncated = serializers.BooleanField(required=False, default=False)


class SemanticRetrievalResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    business_model = serializers.CharField()
    query = serializers.CharField()
    top_k = serializers.IntegerField()
    min_score = serializers.FloatField(allow_null=True)
    embedding = serializers.DictField()
    results = RetrievalResultItemSerializer(many=True)
    context = serializers.DictField()
    message = serializers.CharField(allow_blank=True, required=False, default='')
    score_semantics = serializers.CharField(required=False, allow_blank=True, default='')
    truncation = serializers.DictField(required=False)
