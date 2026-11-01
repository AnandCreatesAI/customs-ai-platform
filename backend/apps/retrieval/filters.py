from __future__ import annotations

from qdrant_client.http import models as qmodels


def build_qdrant_search_filter(
    *,
    business_model_key: str,
    user_id: str,
    document_ids: frozenset[str],
) -> qmodels.Filter:
    must: list[qmodels.Condition] = [
        qmodels.FieldCondition(
            key='business_model_key',
            match=qmodels.MatchValue(value=business_model_key),
        ),
        qmodels.FieldCondition(
            key='user_id',
            match=qmodels.MatchValue(value=user_id),
        ),
        qmodels.FieldCondition(
            key='is_active',
            match=qmodels.MatchValue(value=True),
        ),
    ]
    if document_ids:
        must.append(
            qmodels.FieldCondition(
                key='document_id',
                match=qmodels.MatchAny(any=list(document_ids)),
            )
        )
    return qmodels.Filter(must=must)
