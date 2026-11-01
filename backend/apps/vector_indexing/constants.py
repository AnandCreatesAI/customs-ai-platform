from django.db import models

SKIP_REASON_SEMANTIC_UNAVAILABLE = 'semantic_embeddings_unavailable'

ERROR_INDEXING_INTERRUPTED = 'indexing_interrupted_stale_worker'
ERROR_REQUIRES_RECONCILIATION = 'activation_requires_reconciliation'


class IndexingRunStatus(models.TextChoices):
    QUEUED = 'queued', 'Queued'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    SKIPPED = 'skipped', 'Skipped'
    RETRYING = 'retrying', 'Retrying'


class ChunkVectorIndexStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    INDEXED = 'indexed', 'Indexed'
    FAILED = 'failed', 'Failed'
    SKIPPED_STUB = 'skipped_stub', 'Skipped stub'


class IndexingActivationPhase(models.TextChoices):
    """Durable activation progress on an IndexingRun (PostgreSQL is authoritative)."""

    NONE = 'none', 'None'
    PENDING_RECORDED = 'pending_recorded', 'Pending recorded in PostgreSQL'
    QDRANT_ACTIVATING = 'qdrant_activating', 'Qdrant activation in progress'
    QDRANT_ACTIVATED = 'qdrant_activated', 'Qdrant payloads active; PostgreSQL not committed'
    COMMITTED = 'committed', 'PostgreSQL activation committed'


ACTIVE_INDEXING_STATUSES = frozenset(
    {
        IndexingRunStatus.QUEUED,
        IndexingRunStatus.PROCESSING,
        IndexingRunStatus.RETRYING,
    }
)

DISPATCHABLE_INDEXING_STATUSES = frozenset(ACTIVE_INDEXING_STATUSES)
