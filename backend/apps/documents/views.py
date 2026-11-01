from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.access import documents_for_user, get_document_for_user
from apps.documents.business_model_access import get_active_business_model
from apps.documents.document_storage import DocumentStorageError, store_training_json_input, store_training_text_input, store_training_upload
from apps.documents.pagination import DocumentPageNumberPagination
from apps.documents.serializers import (
    DocumentSerializer,
    JsonTrainingRequestSerializer,
    TextTrainingRequestSerializer,
)
from apps.documents.throttling import DocumentTrainingRateThrottle


class DocumentTrainingAPIView(APIView):
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [DocumentTrainingRateThrottle]

    def _inactive_user_response(self, request: Request) -> Response | None:
        if not request.user.is_active:
            return Response(
                {'detail': 'User account is inactive.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None


class DocumentListView(DocumentTrainingAPIView):
    pagination_class = DocumentPageNumberPagination

    def get(self, request: Request) -> Response:
        inactive = self._inactive_user_response(request)
        if inactive:
            return inactive

        queryset = documents_for_user(request.user).order_by('-created_at')

        business_model_key = request.query_params.get('business_model')
        if business_model_key:
            queryset = queryset.filter(business_model__key=business_model_key.strip())

        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter.strip())

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = DocumentSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class DocumentDetailView(DocumentTrainingAPIView):
    def get(self, request: Request, document_id) -> Response:
        inactive = self._inactive_user_response(request)
        if inactive:
            return inactive

        document = get_document_for_user(request.user, document_id)
        return Response(DocumentSerializer(document).data, status=status.HTTP_200_OK)


class DocumentUploadView(DocumentTrainingAPIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request: Request) -> Response:
        inactive = self._inactive_user_response(request)
        if inactive:
            return inactive

        business_model_key = request.data.get('business_model')
        try:
            business_model = get_active_business_model(business_model_key)
        except ValidationError as exc:
            return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)

        files = request.FILES.getlist('files')
        if not files:
            return Response(
                {'files': ['At least one file is required.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        group_title = (request.data.get('title') or '').strip()
        group_metadata = {'group_title': group_title} if group_title else {}

        results = []
        created_count = 0
        for uploaded in files:
            metadata = dict(group_metadata)
            claimed_content_type = getattr(uploaded, 'content_type', None)
            if claimed_content_type:
                normalized_type = claimed_content_type.split(';', 1)[0].strip().lower()
                if normalized_type in {'application/octet-stream', ''}:
                    claimed_content_type = None
            try:
                document = store_training_upload(
                    user=request.user,
                    business_model=business_model,
                    file_obj=uploaded,
                    original_filename=uploaded.name,
                    claimed_content_type=claimed_content_type,
                    metadata=metadata,
                )
                created_count += 1
                results.append(
                    {
                        'status': 'created',
                        'document': DocumentSerializer(document).data,
                    }
                )
            except DocumentStorageError as exc:
                results.append(
                    {
                        'status': 'error',
                        'filename': uploaded.name,
                        'error': str(exc),
                    }
                )
            except Exception:
                results.append(
                    {
                        'status': 'error',
                        'filename': uploaded.name,
                        'error': 'Upload failed.',
                    }
                )

        if created_count == 0:
            return Response(
                {
                    'business_model': business_model.key,
                    'results': results,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                'business_model': business_model.key,
                'results': results,
            },
            status=status.HTTP_201_CREATED,
        )


class DocumentTextInputView(DocumentTrainingAPIView):
    parser_classes = [JSONParser, FormParser]

    def post(self, request: Request) -> Response:
        inactive = self._inactive_user_response(request)
        if inactive:
            return inactive

        serializer = TextTrainingRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            business_model = get_active_business_model(serializer.validated_data['business_model'])
        except ValidationError as exc:
            return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)

        try:
            document = store_training_text_input(
                user=request.user,
                business_model=business_model,
                title=serializer.validated_data['title'],
                content=serializer.validated_data['content'],
            )
        except DocumentStorageError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        payload = DocumentSerializer(document).data
        return Response(
            {
                'id': payload['id'],
                'title': payload['title'],
                'business_model': payload['business_model'],
                'input_type': payload['input_type'],
                'status': payload['status'],
                'document': payload,
            },
            status=status.HTTP_201_CREATED,
        )


class DocumentJsonInputView(DocumentTrainingAPIView):
    parser_classes = [JSONParser, FormParser]

    def post(self, request: Request) -> Response:
        inactive = self._inactive_user_response(request)
        if inactive:
            return inactive

        serializer = JsonTrainingRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            business_model = get_active_business_model(serializer.validated_data['business_model'])
        except ValidationError as exc:
            return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)

        try:
            document = store_training_json_input(
                user=request.user,
                business_model=business_model,
                title=serializer.validated_data['title'],
                content=serializer.validated_data['content'],
            )
        except DocumentStorageError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        payload = DocumentSerializer(document).data
        return Response(
            {
                'id': payload['id'],
                'title': payload['title'],
                'business_model': payload['business_model'],
                'input_type': payload['input_type'],
                'status': payload['status'],
                'document': payload,
            },
            status=status.HTTP_201_CREATED,
        )
