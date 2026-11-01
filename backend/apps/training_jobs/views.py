from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.business_model_access import get_active_business_model
from apps.training_jobs.access import get_training_job_for_user, training_jobs_for_user
from apps.training_jobs.pagination import TrainingJobPageNumberPagination
from apps.training_jobs.serializers import (
    TrainingJobCreateSerializer,
    TrainingJobSerializer,
    TrainingJobSummarySerializer,
)
from apps.training_jobs.services import (
    TrainingJobServiceError,
    cancel_training_job,
    create_training_jobs,
    retry_training_job,
)
from apps.training_jobs.throttling import TrainingJobRateThrottle


class TrainingJobAPIView(APIView):
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [TrainingJobRateThrottle]

    def _inactive_user_response(self, request: Request) -> Response | None:
        if not request.user.is_active:
            return Response(
                {'detail': 'User account is inactive.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None


class TrainingJobListCreateView(TrainingJobAPIView):
    pagination_class = TrainingJobPageNumberPagination

    def get(self, request: Request) -> Response:
        inactive = self._inactive_user_response(request)
        if inactive:
            return inactive

        queryset = training_jobs_for_user(request.user).order_by('-created_at')

        business_model_key = request.query_params.get('business_model')
        if business_model_key:
            queryset = queryset.filter(business_model__key=business_model_key.strip())

        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter.strip())

        document_id = request.query_params.get('document_id')
        if document_id:
            queryset = queryset.filter(document_id=document_id.strip())

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = TrainingJobSummarySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request) -> Response:
        inactive = self._inactive_user_response(request)
        if inactive:
            return inactive

        serializer = TrainingJobCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            business_model = get_active_business_model(
                serializer.validated_data['business_model']
            )
        except ValidationError as exc:
            return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)

        document_ids = [str(doc_id) for doc_id in serializer.validated_data['document_ids']]

        try:
            jobs = create_training_jobs(
                user=request.user,
                business_model=business_model,
                document_ids=document_ids,
            )
        except ValidationError as exc:
            return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
        except TrainingJobServiceError as exc:
            return Response({'detail': exc.message}, status=status.HTTP_400_BAD_REQUEST)

        payload = TrainingJobSummarySerializer(jobs, many=True).data
        return Response(
            {
                'business_model': business_model.key,
                'jobs': payload,
            },
            status=status.HTTP_201_CREATED,
        )


class TrainingJobDetailView(TrainingJobAPIView):
    def get(self, request: Request, job_id) -> Response:
        inactive = self._inactive_user_response(request)
        if inactive:
            return inactive

        job = get_training_job_for_user(request.user, job_id)
        return Response(TrainingJobSerializer(job).data, status=status.HTTP_200_OK)


class TrainingJobRetryView(TrainingJobAPIView):
    def post(self, request: Request, job_id) -> Response:
        inactive = self._inactive_user_response(request)
        if inactive:
            return inactive

        job = get_training_job_for_user(request.user, job_id)
        try:
            new_job = retry_training_job(job, user=request.user)
        except TrainingJobServiceError as exc:
            return Response({'detail': exc.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(TrainingJobSerializer(new_job).data, status=status.HTTP_201_CREATED)


class TrainingJobCancelView(TrainingJobAPIView):
    def post(self, request: Request, job_id) -> Response:
        inactive = self._inactive_user_response(request)
        if inactive:
            return inactive

        job = get_training_job_for_user(request.user, job_id)
        try:
            cancelled = cancel_training_job(job, user=request.user)
        except TrainingJobServiceError as exc:
            return Response({'detail': exc.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(TrainingJobSerializer(cancelled).data, status=status.HTTP_200_OK)
