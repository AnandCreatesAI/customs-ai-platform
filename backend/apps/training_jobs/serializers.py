from rest_framework import serializers

from apps.documents.models import Document
from apps.training_jobs.models import TrainingJob


class TrainingJobCreateSerializer(serializers.Serializer):
    business_model = serializers.CharField(max_length=32)
    document_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )


class TrainingJobDocumentSummarySerializer(serializers.ModelSerializer):
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
            'file_size',
            'status',
            'created_at',
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


class TrainingJobSerializer(serializers.ModelSerializer):
    business_model = serializers.CharField(source='business_model.key', read_only=True)
    document = TrainingJobDocumentSummarySerializer(read_only=True)
    parent_job_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = TrainingJob
        fields = [
            'id',
            'business_model',
            'document',
            'parent_job_id',
            'status',
            'progress',
            'current_stage',
            'error_message',
            'dispatch_error',
            'retry_count',
            'created_at',
            'started_at',
            'completed_at',
            'updated_at',
        ]
        read_only_fields = fields


class TrainingJobSummarySerializer(serializers.ModelSerializer):
    business_model = serializers.CharField(source='business_model.key', read_only=True)
    document_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = TrainingJob
        fields = [
            'id',
            'business_model',
            'document_id',
            'status',
            'progress',
            'current_stage',
            'error_message',
            'retry_count',
            'dispatch_error',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields
