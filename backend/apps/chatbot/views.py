from django.db import transaction
from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chatbot.chat_context import build_chat_context, build_regenerate_context
from apps.chatbot.factory import get_chatbot_service
from apps.chatbot.serializers import (
    ChatbotMessageRequestSerializer,
    ChatbotRegenerateRequestSerializer,
)
from apps.conversations.models import Message, MessageRole
from apps.conversations.persistence import (
    ConversationAccessError,
    MessagePersistenceError,
    apply_llm_conversation_title,
    get_conversation_for_access,
    persist_assistant_message,
    persist_user_message,
    regenerate_assistant_message,
    resolve_conversation,
)
from apps.conversations.throttling import ChatbotMessageRateThrottle
from apps.rag.exceptions import RagError
from gateways.llm import LLMGatewayError

_PROCESSING_FAILURE_DETAIL = 'Unable to complete the assistant response.'
_ASSISTANT_SAVE_FAILURE_DETAIL = 'Assistant response could not be saved.'


class ChatbotMessageView(APIView):
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [ChatbotMessageRateThrottle]

    def post(self, request: Request) -> Response:
        if not request.user.is_active:
            return Response(
                {'detail': 'User account is inactive.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ChatbotMessageRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        model_key = serializer.validated_data['model_key']
        message = serializer.validated_data['message']
        conversation_id = serializer.validated_data.get('conversation_id')
        business_model = serializer.business_model

        try:
            with transaction.atomic():
                conversation, created = resolve_conversation(
                    user=request.user,
                    business_model=business_model,
                    conversation_id=conversation_id,
                    lock=conversation_id is not None,
                )
                persist_user_message(
                    conversation=conversation,
                    content=message,
                )
        except ConversationAccessError as exc:
            return Response({'detail': str(exc)}, status=exc.status_code)
        except MessagePersistenceError:
            return Response(
                {'detail': 'Unable to save message.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        conversation_ref = str(conversation.id)
        chat_context = build_chat_context(
            conversation=conversation,
            is_new_conversation=created,
            user_message=message,
        )
        chat_context['user'] = request.user

        service = get_chatbot_service()
        try:
            llm_response = service.process_message_response(model_key, message, chat_context)
        except RagError as exc:
            return Response(
                {
                    'detail': exc.message,
                    'code': getattr(exc, 'code', 'rag_error'),
                    'conversation_id': conversation_ref,
                },
                status=getattr(exc, 'http_status', status.HTTP_502_BAD_GATEWAY),
            )
        except ValueError:
            return Response(
                {
                    'detail': _PROCESSING_FAILURE_DETAIL,
                    'conversation_id': conversation_ref,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except LLMGatewayError as exc:
            return Response(
                {
                    'detail': str(exc),
                    'conversation_id': conversation_ref,
                },
                status=_map_gateway_error_status(exc),
            )

        metadata = llm_response.metadata or {}
        provider = metadata.get('provider') or service.gateways.llm.provider_name
        model_name = metadata.get('model') or service.gateways.llm.model_name

        if created:
            apply_llm_conversation_title(
                conversation,
                metadata.get('conversation_title'),
                user_message_fallback=message,
            )

        try:
            assistant_message = persist_assistant_message(
                conversation=conversation,
                llm_response=llm_response,
                provider_key=provider,
                model_name=model_name,
            )
        except MessagePersistenceError:
            return Response(
                {
                    'detail': _ASSISTANT_SAVE_FAILURE_DETAIL,
                    'conversation_id': conversation_ref,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        conversation.refresh_from_db()
        return Response(
            _success_payload(
                model_key=model_key,
                provider=provider,
                model_name=model_name,
                response=llm_response.content,
                conversation=conversation,
                assistant_message=assistant_message,
            ),
            status=status.HTTP_200_OK,
        )


class ChatbotRegenerateView(APIView):
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [ChatbotMessageRateThrottle]

    def post(self, request: Request) -> Response:
        if not request.user.is_active:
            return Response(
                {'detail': 'User account is inactive.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ChatbotRegenerateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        model_key = serializer.validated_data['model_key']
        conversation_id = serializer.validated_data['conversation_id']
        assistant_message_id = serializer.validated_data['assistant_message_id']

        try:
            conversation = get_conversation_for_access(
                user=request.user,
                conversation_id=conversation_id,
                require_active=True,
            )
        except ConversationAccessError as exc:
            return Response({'detail': str(exc)}, status=exc.status_code)

        authoritative_model_key = conversation.business_model.key
        if model_key != authoritative_model_key:
            return Response(
                {'detail': 'Conversation does not match the selected business model.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            assistant_message = Message.objects.select_related('conversation').get(
                pk=assistant_message_id,
                conversation=conversation,
                role=MessageRole.ASSISTANT,
            )
        except Message.DoesNotExist:
            return Response(
                {'detail': 'Assistant message not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        user_message = _preceding_user_message(conversation, assistant_message)
        if user_message is None:
            return Response(
                {'detail': 'Unable to locate the user message for regeneration.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        chat_context = build_regenerate_context(
            conversation=conversation,
            user_message=user_message.content,
            assistant_message_id=assistant_message.id,
        )
        chat_context['user'] = request.user

        service = get_chatbot_service()
        try:
            llm_response = service.process_message_response(
                authoritative_model_key,
                user_message.content,
                chat_context,
            )
        except RagError as exc:
            return Response(
                {
                    'detail': exc.message,
                    'code': getattr(exc, 'code', 'rag_error'),
                },
                status=getattr(exc, 'http_status', status.HTTP_502_BAD_GATEWAY),
            )
        except ValueError:
            return Response(
                {'detail': _PROCESSING_FAILURE_DETAIL},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except LLMGatewayError as exc:
            return Response(
                {'detail': str(exc)},
                status=_map_gateway_error_status(exc),
            )

        metadata = llm_response.metadata or {}
        provider = metadata.get('provider') or service.gateways.llm.provider_name
        model_name = metadata.get('model') or service.gateways.llm.model_name

        try:
            assistant_message = regenerate_assistant_message(
                assistant_message=assistant_message,
                llm_response=llm_response,
                provider_key=provider,
                model_name=model_name,
            )
        except MessagePersistenceError:
            return Response(
                {'detail': _ASSISTANT_SAVE_FAILURE_DETAIL},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        conversation.refresh_from_db()
        return Response(
            _success_payload(
                model_key=authoritative_model_key,
                provider=provider,
                model_name=model_name,
                response=llm_response.content,
                conversation=conversation,
                assistant_message=assistant_message,
            ),
            status=status.HTTP_200_OK,
        )


def _preceding_user_message(conversation, assistant_message: Message) -> Message | None:
    return (
        conversation.messages.filter(role=MessageRole.USER, created_at__lte=assistant_message.created_at)
        .order_by('-created_at', '-id')
        .first()
    )


def _success_payload(
    *,
    model_key: str,
    provider: str,
    model_name: str,
    response: str,
    conversation,
    assistant_message: Message,
) -> dict:
    metadata = assistant_message.metadata if isinstance(assistant_message.metadata, dict) else {}
    suggestions = metadata.get('suggested_questions')
    if not isinstance(suggestions, list):
        suggestions = []
    payload = {
        'success': True,
        'model_key': model_key,
        'provider': provider,
        'model': model_name,
        'response': response,
        'conversation_id': str(conversation.id),
        'conversation_title': conversation.title,
        'assistant_message_id': str(assistant_message.id),
        'suggested_questions': suggestions,
    }
    sources = metadata.get('sources')
    if isinstance(sources, list):
        payload['sources'] = sources
    else:
        payload['sources'] = []
    evidence_status = metadata.get('evidence_status')
    if isinstance(evidence_status, str) and evidence_status:
        payload['evidence_status'] = evidence_status
    evidence_detail = metadata.get('evidence_detail')
    if isinstance(evidence_detail, dict):
        payload['evidence_detail'] = evidence_detail
    return payload


def _map_gateway_error_status(exc: LLMGatewayError) -> int:
    message = str(exc)
    if message == 'Gemini model temporarily unavailable':
        return status.HTTP_503_SERVICE_UNAVAILABLE
    if message in ('Gemini generation deadline exceeded', 'Gemini request timed out'):
        return status.HTTP_504_GATEWAY_TIMEOUT
    if message == 'Gemini service unavailable':
        return status.HTTP_503_SERVICE_UNAVAILABLE
    return status.HTTP_502_BAD_GATEWAY
