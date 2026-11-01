from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.conversations.models import Conversation
from apps.conversations.pagination import ConversationPageNumberPagination
from apps.conversations.persistence import (
    ConversationAccessError,
    get_conversation_for_access,
    messages_for_conversation,
)
from apps.conversations.serializers import (
    ConversationDetailSerializer,
    ConversationSummarySerializer,
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

        queryset = (
            Conversation.objects.filter(user=request.user)
            .select_related('business_model')
            .order_by('-updated_at', '-id')
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
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
        serializer = MessageHistorySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
