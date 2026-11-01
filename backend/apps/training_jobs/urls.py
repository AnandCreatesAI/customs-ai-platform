from django.urls import path

from apps.training_jobs.views import (
    TrainingJobCancelView,
    TrainingJobDetailView,
    TrainingJobListCreateView,
    TrainingJobRetryView,
)

urlpatterns = [
    path('jobs/', TrainingJobListCreateView.as_view(), name='training-job-list-create'),
    path('jobs/<uuid:job_id>/', TrainingJobDetailView.as_view(), name='training-job-detail'),
    path('jobs/<uuid:job_id>/retry/', TrainingJobRetryView.as_view(), name='training-job-retry'),
    path('jobs/<uuid:job_id>/cancel/', TrainingJobCancelView.as_view(), name='training-job-cancel'),
]
