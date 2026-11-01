from rest_framework import serializers

from apps.documents.models import Document


class DocumentSerializer(serializers.ModelSerializer):
    business_model = serializers.CharField(source='business_model.key', read_only=True)
    input_type = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id',
            'original_filename',
            'title',
            'business_model',
            'input_type',
            'file_type',
            'mime_type',
            'file_size',
            'checksum',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_input_type(self, obj: Document) -> str:
        value = obj.metadata.get('input_type')
        return str(value) if value else 'file'

    def get_title(self, obj: Document) -> str:
        meta_title = obj.metadata.get('title')
        if meta_title:
            return str(meta_title)
        return obj.original_filename


class TextTrainingRequestSerializer(serializers.Serializer):
    business_model = serializers.CharField(max_length=32)
    title = serializers.CharField(max_length=255)
    content = serializers.CharField()


class JsonTrainingRequestSerializer(serializers.Serializer):
    business_model = serializers.CharField(max_length=32)
    title = serializers.CharField(max_length=255)
    content = serializers.CharField()
