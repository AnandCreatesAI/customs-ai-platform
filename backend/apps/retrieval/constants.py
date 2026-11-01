from django.db import models

# Qdrant collection distance for Phase 5/6 semantic collections (see gateways.qdrant.client).
QDRANT_DISTANCE_METRIC = 'cosine'

# Gemini embeddings are raw vectors; Qdrant applies cosine similarity on stored/query vectors.
EMBEDDING_NORMALIZATION_POLICY = 'provider_raw_cosine'


class RetrievalStatus(models.TextChoices):
    OK = 'ok', 'Ok'
    NO_INDEXED_CONTENT = 'no_indexed_content', 'No indexed content'
    SEMANTIC_UNAVAILABLE = 'semantic_unavailable', 'Semantic retrieval unavailable'
