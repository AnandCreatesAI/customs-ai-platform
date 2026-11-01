from rest_framework import serializers

from apps.conversations.models import Conversation, Message, MessageFeedbackRating
from apps.conversations.titles import is_placeholder_conversation_title


class ConversationSummarySerializer(serializers.ModelSerializer):
    model_key = serializers.CharField(source='business_model.key', read_only=True)

    class Meta:
        model = Conversation
        fields = (
            'id',
            'title',
            'model_key',
            'is_pinned',
            'is_active',
            'created_at',
            'updated_at',
        )


class MessageHistorySerializer(serializers.ModelSerializer):
    suggested_questions = serializers.SerializerMethodField()
    feedback_rating = serializers.SerializerMethodField()
    sources = serializers.SerializerMethodField()
    evidence_status = serializers.SerializerMethodField()
    evidence_detail = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            'id',
            'role',
            'content',
            'provider_key',
            'model_name',
            'created_at',
            'suggested_questions',
            'feedback_rating',
            'sources',
            'evidence_status',
            'evidence_detail',
        )

    def get_suggested_questions(self, obj: Message) -> list[str]:
        metadata = obj.metadata if isinstance(obj.metadata, dict) else {}
        suggestions = metadata.get('suggested_questions')
        if not isinstance(suggestions, list):
            return []
        return [item for item in suggestions if isinstance(item, str) and item.strip()]

    def get_feedback_rating(self, obj: Message) -> int | None:
        request = self.context.get('request')
        if request is None or not hasattr(request, 'user'):
            return None
        feedback = obj.feedback_entries.filter(user=request.user).first()
        return feedback.rating if feedback else None

    def get_sources(self, obj: Message) -> list[dict]:
        if obj.role != 'assistant':
            return []
        metadata = obj.metadata if isinstance(obj.metadata, dict) else {}
        sources = metadata.get('sources')
        if not isinstance(sources, list):
            return []
        sanitized: list[dict] = []
        for item in sources:
            if not isinstance(item, dict):
                continue
            ref = item.get('ref')
            chunk_id = item.get('chunk_id')
            document_id = item.get('document_id')
            if not isinstance(ref, int) or not chunk_id or not document_id:
                continue
            entry = {
                'ref': ref,
                'chunk_id': str(chunk_id),
                'document_id': str(document_id),
                'document_filename': str(item.get('document_filename') or ''),
                'chunk_index': int(item.get('chunk_index') or 0),
                'score': float(item.get('score') or 0.0),
                'artifact_version': int(item.get('artifact_version') or 0),
            }
            sanitized.append(entry)
        return sanitized

    def get_evidence_status(self, obj: Message) -> str | None:
        if obj.role != 'assistant':
            return None
        metadata = obj.metadata if isinstance(obj.metadata, dict) else {}
        status = metadata.get('evidence_status')
        if isinstance(status, str) and status.strip():
            return status.strip()
        return None

    def get_evidence_detail(self, obj: Message) -> dict | None:
        if obj.role != 'assistant':
            return None
        metadata = obj.metadata if isinstance(obj.metadata, dict) else {}
        detail = metadata.get('evidence_detail')
        if not isinstance(detail, dict):
            return None
        truncation = detail.get('truncation')
        return {
            'retrieval_status': str(detail.get('retrieval_status') or ''),
            'chunk_count': int(detail.get('chunk_count') or 0),
            'context_truncated': bool(detail.get('context_truncated')),
            'score_semantics': str(detail.get('score_semantics') or ''),
            'truncation': truncation if isinstance(truncation, dict) else {},
        }


class ConversationTitleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ('title',)

    def validate_title(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError('Title cannot be empty.')
        if is_placeholder_conversation_title(cleaned):
            raise serializers.ValidationError('Choose a specific title for this conversation.')
        return cleaned


class ConversationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ('title', 'is_pinned')

    def validate_title(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError('Title cannot be empty.')
        if is_placeholder_conversation_title(cleaned):
            raise serializers.ValidationError('Choose a specific title for this conversation.')
        return cleaned


class ConversationDetailSerializer(serializers.ModelSerializer):
    model_key = serializers.CharField(source='business_model.key', read_only=True)

    class Meta:
        model = Conversation
        fields = (
            'id',
            'title',
            'model_key',
            'is_pinned',
            'is_active',
            'created_at',
            'updated_at',
        )


class MessageFeedbackSerializer(serializers.Serializer):
    rating = serializers.ChoiceField(choices=[MessageFeedbackRating.UP, MessageFeedbackRating.DOWN])
