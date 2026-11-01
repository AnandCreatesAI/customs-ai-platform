"""
Central TrainingJob status lifecycle (all BusinessModel keys).

Future Celery workers must call ``transition_training_job`` rather than mutating status directly.
"""

from __future__ import annotations

from apps.training_jobs.models import TrainingJobStatus

TERMINAL_STATUSES = frozenset(
    {
        TrainingJobStatus.COMPLETED,
        TrainingJobStatus.FAILED,
        TrainingJobStatus.CANCELLED,
    }
)

ACTIVE_STATUSES = frozenset(
    {
        TrainingJobStatus.QUEUED,
        TrainingJobStatus.PROCESSING,
        TrainingJobStatus.RETRYING,
    }
)

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    TrainingJobStatus.QUEUED: frozenset(
        {TrainingJobStatus.PROCESSING, TrainingJobStatus.CANCELLED}
    ),
    TrainingJobStatus.PROCESSING: frozenset(
        {
            TrainingJobStatus.COMPLETED,
            TrainingJobStatus.FAILED,
            TrainingJobStatus.RETRYING,
        }
    ),
    TrainingJobStatus.RETRYING: frozenset(
        {TrainingJobStatus.QUEUED, TrainingJobStatus.PROCESSING}
    ),
    TrainingJobStatus.FAILED: frozenset(),
    TrainingJobStatus.COMPLETED: frozenset(),
    TrainingJobStatus.CANCELLED: frozenset(),
}


class InvalidJobTransitionError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def validate_transition(current: str, new: str) -> None:
    if current == new:
        return
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if new not in allowed:
        raise InvalidJobTransitionError(
            f'Cannot transition job from {current} to {new}.'
        )


def validate_progress_for_status(*, status: str, progress: int) -> None:
    if progress < 0 or progress > 100:
        raise InvalidJobTransitionError('Progress must be between 0 and 100.')

    if status == TrainingJobStatus.COMPLETED and progress != 100:
        raise InvalidJobTransitionError('Completed jobs must have progress 100.')

    if status in TERMINAL_STATUSES and status != TrainingJobStatus.COMPLETED:
        if progress == 100 and status != TrainingJobStatus.COMPLETED:
            raise InvalidJobTransitionError(
                'Progress 100 is only valid for completed jobs.'
            )
