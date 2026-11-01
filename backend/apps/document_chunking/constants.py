from django.db import models

CHUNKING_VERSION = '1.0.0'
VECTOR_DTYPE_FLOAT32 = 'float32'
VECTOR_SERIALIZATION_VERSION = 1


class ChunkingRunStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    RUNNING = 'running', 'Running'
    SUCCEEDED = 'succeeded', 'Succeeded'
    FAILED = 'failed', 'Failed'


class ChunkEmbeddingStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    SUCCEEDED = 'succeeded', 'Succeeded'
    FAILED = 'failed', 'Failed'


class VectorKind(models.TextChoices):
    STUB_NON_SEMANTIC = 'stub_non_semantic', 'Stub non-semantic'
    SEMANTIC = 'semantic', 'Semantic'
