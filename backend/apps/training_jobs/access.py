from django.shortcuts import get_object_or_404

from apps.training_jobs.models import TrainingJob


def training_jobs_for_user(user):
    return TrainingJob.objects.filter(user=user).select_related(
        'business_model',
        'document',
        'parent_job',
    )


def get_training_job_for_user(user, job_id):
    return get_object_or_404(training_jobs_for_user(user), id=job_id)
