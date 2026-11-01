from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.db import close_old_connections
from kombu.exceptions import OperationalError

from apps.vector_indexing.services import IndexingServiceError, run_indexing_run
from gateways.qdrant.exceptions import QdrantUnavailableError

logger = logging.getLogger(__name__)

TASK_NAME = 'vector_indexing.process_indexing_run'


@shared_task(
    bind=True,
    name=TASK_NAME,
    acks_late=True,
    autoretry_for=(OperationalError, QdrantUnavailableError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=settings.QDRANT_MAX_RETRIES,
)
def process_indexing_run(self, indexing_run_id: str) -> str:
    close_old_connections()
    logger.info(
        'indexing_task_received run_id=%s task_id=%s retry=%s',
        indexing_run_id,
        self.request.id,
        self.request.retries,
    )
    try:
        run_indexing_run(str(indexing_run_id))
        return 'completed'
    except QdrantUnavailableError:
        logger.warning(
            'indexing_run_transient_failure run_id=%s retries=%s',
            indexing_run_id,
            self.request.retries,
        )
        raise
    except IndexingServiceError as exc:
        if exc.transient:
            logger.warning(
                'indexing_run_transient_service_failure run_id=%s error=%s',
                indexing_run_id,
                exc.message,
            )
            raise QdrantUnavailableError(exc.message) from exc
        logger.warning('indexing_run_failed run_id=%s error=%s', indexing_run_id, exc.message)
        return 'failed'
    finally:
        close_old_connections()
