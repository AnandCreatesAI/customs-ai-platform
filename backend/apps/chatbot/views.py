from django.db import transaction
from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chatbot.factory import get_chatbot_service
from apps.chatbot.serializers import ChatbotMessageRequestSerializer
from apps.conversations.persistence import (
    ConversationAccessError,
    MessagePersistenceError,
    persist_assistant_message,
    persist_user_message,
    resolve_conversation,
)
from apps.conversations.throttling import ChatbotMessageRateThrottle
from llm_gateway import LLMGatewayError

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
                conversation, _created = resolve_conversation(
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

        service = get_chatbot_service()
        try:
            llm_response = service.process_message_response(model_key, message)
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
        provider = metadata.get('provider') or service.llm_gateway.provider_name
        model_name = metadata.get('model') or service.llm_gateway.model_name

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

        return Response(
            {
                'success': True,
                'model_key': model_key,
                'provider': provider,
                'model': model_name,
                'response': llm_response.content,
                'conversation_id': conversation_ref,
                'assistant_message_id': str(assistant_message.id),
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
