import logging
import uuid

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chatbot.factory import get_chatbot_service
from apps.chatbot.public_security import (
    evaluate_public_chat_input,
    screen_public_chat_output,
)
from apps.chatbot.public_serializers import PublicChatMessageRequestSerializer
from apps.chatbot.public_throttling import PublicChatRateThrottle
from apps.chatbot.services import PUBLIC_CHAT_MODEL_KEY
from gateways.llm import LLMGatewayError

logger = logging.getLogger(__name__)

_PROCESSING_FAILURE_DETAIL = 'Unable to complete the assistant response.'


def _client_ip(request: Request) -> str:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or 'unknown'


class PublicChatMessageView(APIView):
    """Anonymous general-information chat (no session, no RAG, no persistence)."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [PublicChatRateThrottle]

    def post(self, request: Request) -> Response:
        if not getattr(settings, 'PUBLIC_CHAT_ENABLED', True):
            return Response(
                {'detail': 'Public chat is not available.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        serializer = PublicChatMessageRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        message = serializer.validated_data['message']
        client_conversation_id = serializer.validated_data.get('client_conversation_id')
        conversation_ref = (
            str(client_conversation_id) if client_conversation_id else str(uuid.uuid4())
        )

        refusal = evaluate_public_chat_input(message)
        if refusal is not None:
            logger.info(
                'public_chat_refused ip=%s code=%s len=%s',
                _client_ip(request),
                refusal.code,
                len(message),
            )
            return Response(
                {'detail': refusal.message, 'code': refusal.code},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = get_chatbot_service()
        try:
            llm_response = service.process_public_message_response(
                message,
                {'is_new_conversation': client_conversation_id is None},
            )
        except ValueError:
            return Response(
                {'detail': _PROCESSING_FAILURE_DETAIL},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except LLMGatewayError as exc:
            return Response({'detail': str(exc)}, status=_map_gateway_error_status(exc))

        output_refusal = screen_public_chat_output(llm_response.content)
        if output_refusal is not None:
            logger.warning(
                'public_chat_output_blocked ip=%s code=%s',
                _client_ip(request),
                output_refusal.code,
            )
            return Response(
                {'detail': output_refusal.message, 'code': output_refusal.code},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        metadata = llm_response.metadata or {}
        provider = metadata.get('provider') or service.llm_gateway.provider_name
        model_name = metadata.get('model') or service.llm_gateway.model_name
        suggestions = metadata.get('suggested_questions')
        if not isinstance(suggestions, list):
            suggestions = []

        logger.info(
            'public_chat_ok ip=%s model=%s conv_len=%s',
            _client_ip(request),
            PUBLIC_CHAT_MODEL_KEY,
            len(message),
        )

        return Response(
            {
                'success': True,
                'model_key': PUBLIC_CHAT_MODEL_KEY,
                'provider': provider,
                'model': model_name,
                'response': llm_response.content,
                'conversation_id': conversation_ref,
                'assistant_message_id': str(uuid.uuid4()),
                'suggested_questions': suggestions,
                'sources': [],
                'evidence_status': 'not_applicable',
            },
            status=status.HTTP_200_OK,
        )


def _map_gateway_error_status(exc: LLMGatewayError) -> int:
    message = str(exc)
    if message == 'Gemini model temporarily unavailable':
        return status.HTTP_503_SERVICE_UNAVAILABLE
    if message in ('Gemini generation deadline exceeded', 'Gemini request timed out'):
        return status.HTTP_504_GATEWAY_TIMEOUT
    if message == 'Gemini service unavailable':
        return status.HTTP_503_SERVICE_UNAVAILABLE
    return status.HTTP_502_BAD_GATEWAY
