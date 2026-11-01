from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.retrieval.exceptions import (
    ActivationConsistencyError,
    EmbeddingCompatibilityError,
    RetrievalAccessError,
    RetrievalError,
    RetrievalValidationError,
    SemanticRetrievalUnavailableError,
)
from apps.retrieval.query_processor import process_retrieval_query
from apps.retrieval.serializers import SemanticRetrievalRequestSerializer, SemanticRetrievalResponseSerializer
from apps.retrieval.services import RetrievalServiceResult, retrieve_semantic


class SemanticRetrievalAPIView(APIView):
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        if not request.user.is_active:
            return Response({'detail': 'User account is inactive.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = SemanticRetrievalRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            processed = process_retrieval_query(
                user=request.user,
                business_model_key=serializer.validated_data['business_model'],
                query_text=serializer.validated_data['query'],
                top_k=serializer.validated_data.get('top_k'),
                min_score=serializer.validated_data.get('min_score'),
            )
            document_ids = serializer.validated_data.get('document_ids')
            if document_ids is not None:
                document_ids = [str(doc_id) for doc_id in document_ids]
            result = retrieve_semantic(processed=processed, document_ids=document_ids)
        except RetrievalValidationError as exc:
            return Response({'detail': exc.message, 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        except RetrievalAccessError as exc:
            return Response({'detail': exc.message, 'code': exc.code}, status=status.HTTP_403_FORBIDDEN)
        except ActivationConsistencyError as exc:
            return Response({'detail': exc.message, 'code': exc.code}, status=status.HTTP_409_CONFLICT)
        except EmbeddingCompatibilityError as exc:
            return Response({'detail': exc.message, 'code': exc.code}, status=status.HTTP_409_CONFLICT)
        except SemanticRetrievalUnavailableError as exc:
            return Response({'detail': exc.message, 'code': exc.code}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except RetrievalError as exc:
            return Response({'detail': exc.message, 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)

        payload = _serialize_result(result)
        return Response(payload, status=status.HTTP_200_OK)


def _serialize_result(result: RetrievalServiceResult) -> dict:
    return SemanticRetrievalResponseSerializer(
        {
            'status': result.status,
            'business_model': result.business_model_key,
            'query': result.query,
            'top_k': result.top_k,
            'min_score': result.min_score,
            'embedding': result.embedding,
            'results': [
                {
                    'chunk_id': item.chunk_id,
                    'document_id': item.document_id,
                    'score': item.score,
                    'chunk_index': item.chunk_index,
                    'content': item.content,
                    'element_type': item.element_type,
                    'source_type': item.source_type,
                    'artifact_version': item.artifact_version,
                    'content_hash': item.content_hash,
                    'truncated': item.truncated,
                }
                for item in result.results
            ],
            'context': result.context,
            'message': result.message,
            'score_semantics': result.score_semantics,
            'truncation': result.context.get('truncation', {}),
        }
    ).data
