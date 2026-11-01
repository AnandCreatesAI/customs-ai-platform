from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.conversations.models import Conversation, Message, MessageFeedback, MessageFeedbackRating, MessageRole
from apps.conversations.pagination import ConversationPageNumberPagination
from apps.conversations.persistence import (
    ConversationAccessError,
    backfill_conversation_title,
    conversations_for_recent_chats,
    refresh_legacy_deterministic_title,
    get_conversation_for_access,
    messages_for_conversation,
)
from apps.conversations.serializers import (
    ConversationDetailSerializer,
    ConversationSummarySerializer,
    ConversationUpdateSerializer,
    MessageFeedbackSerializer,
    MessageHistorySerializer,
)
from apps.conversations.throttling import ConversationHistoryRateThrottle


class ConversationListView(APIView):
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [ConversationHistoryRateThrottle]
    pagination_class = ConversationPageNumberPagination

    def get(self, request: Request) -> Response:
        if not request.user.is_active:
            return Response(
                {'detail': 'User account is inactive.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        queryset = conversations_for_recent_chats(request.user)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            for conversation in page:
                backfill_conversation_title(conversation)
                refresh_legacy_deterministic_title(conversation)
        serializer = ConversationSummarySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ConversationDetailView(APIView):
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [ConversationHistoryRateThrottle]

    def get(self, request: Request, conversation_id) -> Response:
        if not request.user.is_active:
            return Response(
                {'detail': 'User account is inactive.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            conversation = get_conversation_for_access(
                user=request.user,
                conversation_id=conversation_id,
                require_active=True,
            )
        except ConversationAccessError as exc:
            return Response({'detail': str(exc)}, status=exc.status_code)

        serializer = ConversationDetailSerializer(conversation)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request: Request, conversation_id) -> Response:
        if not request.user.is_active:
            return Response(
                {'detail': 'User account is inactive.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            conversation = get_conversation_for_access(
                user=request.user,
                conversation_id=conversation_id,
                require_active=True,
            )
        except ConversationAccessError as exc:
            return Response({'detail': str(exc)}, status=exc.status_code)

        serializer = ConversationUpdateSerializer(
            conversation,
            data=request.data,
            partial=True,
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        conversation.refresh_from_db()
        return Response(
            ConversationDetailSerializer(conversation).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request: Request, conversation_id) -> Response:
        if not request.user.is_active:
            return Response(
                {'detail': 'User account is inactive.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            conversation = get_conversation_for_access(
                user=request.user,
                conversation_id=conversation_id,
                require_active=True,
            )
        except ConversationAccessError as exc:
            return Response({'detail': str(exc)}, status=exc.status_code)

        conversation.is_active = False
        conversation.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConversationMessageListView(APIView):
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [ConversationHistoryRateThrottle]
    pagination_class = ConversationPageNumberPagination

    def get(self, request: Request, conversation_id) -> Response:
        if not request.user.is_active:
            return Response(
                {'detail': 'User account is inactive.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            conversation = get_conversation_for_access(
                user=request.user,
                conversation_id=conversation_id,
                require_active=True,
            )
        except ConversationAccessError as exc:
            return Response({'detail': str(exc)}, status=exc.status_code)

        queryset = messages_for_conversation(conversation)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = MessageHistorySerializer(
            page,
            many=True,
            context={'request': request},
        )
        return paginator.get_paginated_response(serializer.data)


class MessageFeedbackView(APIView):
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [ConversationHistoryRateThrottle]

    def put(self, request: Request, message_id) -> Response:
        if not request.user.is_active:
            return Response(
                {'detail': 'User account is inactive.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = MessageFeedbackSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            message = Message.objects.select_related('conversation').get(pk=message_id)
        except Message.DoesNotExist:
            return Response({'detail': 'Message not found.'}, status=status.HTTP_404_NOT_FOUND)

        if message.role != MessageRole.ASSISTANT:
            return Response(
                {'detail': 'Feedback is only supported for assistant messages.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            get_conversation_for_access(
                user=request.user,
                conversation_id=message.conversation_id,
                require_active=True,
            )
        except ConversationAccessError as exc:
            return Response({'detail': str(exc)}, status=exc.status_code)

        rating = serializer.validated_data['rating']
        feedback, _created = MessageFeedback.objects.update_or_create(
            message=message,
            user=request.user,
            defaults={'rating': rating},
        )
        return Response(
            {
                'message_id': str(message.id),
                'rating': feedback.rating,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request: Request, message_id) -> Response:
        if not request.user.is_active:
            return Response(
                {'detail': 'User account is inactive.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            message = Message.objects.select_related('conversation').get(pk=message_id)
        except Message.DoesNotExist:
            return Response({'detail': 'Message not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            get_conversation_for_access(
                user=request.user,
                conversation_id=message.conversation_id,
                require_active=True,
            )
        except ConversationAccessError as exc:
            return Response({'detail': str(exc)}, status=exc.status_code)

        MessageFeedback.objects.filter(message=message, user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
