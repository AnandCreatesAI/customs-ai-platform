from typing import Any

from django.conf import settings

from apps.authentication.models import User
from apps.chatbot.structured_output import (
    ParsedStructuredChatResponse,
    parse_structured_chat_response,
    structured_output_system_addon,
)
from apps.rag.citations import validate_answer_citations
from apps.rag.metadata import build_rag_message_metadata
from apps.rag.orchestrator import run_rag_retrieval
from apps.rag.prompts import compose_rag_system_prompt, rag_structured_output_addon
from apps.rag.schemas import RagGroundedContext, RagNoSourcesOutcome
from gateways.llm import LLMGateway, LLMRequest, LLMResponse
from model_handlers.registry import MODEL_HANDLER_CLASSES, get_model_handler


class ChatbotService:
    """Orchestrates model handler selection for chat flows (no HTTP/WebSocket layer)."""

    def __init__(self, llm_gateway: LLMGateway) -> None:
        if llm_gateway is None:
            raise ValueError('llm_gateway is required')
        self._llm_gateway = llm_gateway

    @property
    def llm_gateway(self) -> LLMGateway:
        return self._llm_gateway

    @staticmethod
    def supported_model_keys() -> list[str]:
        return sorted(MODEL_HANDLER_CLASSES.keys())

    def process_message(
        self,
        model_key: str,
        user_message: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        return self.process_structured_turn(model_key, user_message, context).answer

    def process_message_response(
        self,
        model_key: str,
        user_message: str,
        context: dict[str, Any] | None = None,
    ) -> LLMResponse:
        if settings.RAG_ENABLED:
            # Fail-closed: retrieval errors propagate; no ungrounded LLM fallback.
            return self._process_rag_message_response(model_key, user_message, context)
        parsed = self.process_structured_turn(model_key, user_message, context)
        return self._llm_response_from_parsed(parsed)

    def process_structured_turn(
        self,
        model_key: str,
        user_message: str,
        context: dict[str, Any] | None = None,
    ) -> ParsedStructuredChatResponse:
        if settings.RAG_ENABLED:
            response = self._process_rag_message_response(model_key, user_message, context)
            metadata = response.metadata or {}
            return ParsedStructuredChatResponse(
                answer=response.content,
                conversation_title=metadata.get('conversation_title'),
                suggested_questions=list(metadata.get('suggested_questions') or []),
            )

        context_data = dict(context or {})
        is_new = bool(context_data.get('is_new_conversation'))

        handler = get_model_handler(model_key, self._llm_gateway)
        system_prompt = handler.build_system_prompt().strip()
        system_prompt = f'{system_prompt}{structured_output_system_addon(context_data)}'

        request = LLMRequest(
            prompt=user_message,
            system_prompt=system_prompt,
            metadata={'model_key': model_key, 'context': context_data},
        )
        raw_response = self._llm_gateway.generate(request)

        return parse_structured_chat_response(
            raw_response.content,
            is_new_conversation=is_new,
            user_message_for_title_fallback=user_message,
            rag_enabled=False,
        )

    def _process_rag_message_response(
        self,
        model_key: str,
        user_message: str,
        context: dict[str, Any] | None,
    ) -> LLMResponse:
        context_data = dict(context or {})
        user = context_data.get('user')
        if not isinstance(user, User):
            raise ValueError('RAG requires an authenticated user in chat context.')

        is_new = bool(context_data.get('is_new_conversation'))
        outcome = run_rag_retrieval(
            user=user,
            business_model_key=model_key,
            query_text=user_message,
        )

        if isinstance(outcome, RagNoSourcesOutcome):
            metadata = build_rag_message_metadata(
                suggested_questions=[],
                sources=[],
                evidence_status=outcome.evidence_status,
                evidence_detail=outcome.evidence_detail,
                retrieval_meta=outcome.retrieval_meta,
            )
            return LLMResponse(content=outcome.answer, metadata=metadata)

        return self._generate_grounded_rag_response(
            model_key=model_key,
            user_message=user_message,
            context_data=context_data,
            grounded=outcome,
            is_new_conversation=is_new,
        )

    def _generate_grounded_rag_response(
        self,
        *,
        model_key: str,
        user_message: str,
        context_data: dict[str, Any],
        grounded: RagGroundedContext,
        is_new_conversation: bool,
    ) -> LLMResponse:
        handler = get_model_handler(model_key, self._llm_gateway)
        structured_addon = structured_output_system_addon(context_data)
        rag_addon = rag_structured_output_addon(context_data, source_count=len(grounded.sources))
        system_prompt = compose_rag_system_prompt(
            handler=handler,
            reference_blocks=grounded.reference_blocks,
            structured_output_addon=f'{structured_addon}{rag_addon}',
        )

        request = LLMRequest(
            prompt=user_message,
            system_prompt=system_prompt,
            metadata={'model_key': model_key, 'context': context_data, 'rag': True},
        )
        raw_response = self._llm_gateway.generate(request)

        parsed = parse_structured_chat_response(
            raw_response.content,
            is_new_conversation=is_new_conversation,
            user_message_for_title_fallback=user_message,
            rag_enabled=True,
        )

        valid_refs = {source.ref for source in grounded.sources}
        validate_answer_citations(answer=parsed.answer, valid_refs=valid_refs)

        metadata = build_rag_message_metadata(
            suggested_questions=parsed.suggested_questions,
            sources=grounded.sources,
            evidence_status=grounded.evidence_status,
            evidence_detail=grounded.evidence_detail,
            retrieval_meta=grounded.retrieval_meta,
        )
        if parsed.conversation_title:
            metadata['conversation_title'] = parsed.conversation_title

        provider = self._llm_gateway.provider_name
        model_name = self._llm_gateway.model_name
        metadata['provider'] = provider
        metadata['model'] = model_name

        return LLMResponse(content=parsed.answer, metadata=metadata)

    @staticmethod
    def _llm_response_from_parsed(parsed: ParsedStructuredChatResponse) -> LLMResponse:
        metadata: dict[str, Any] = {
            'suggested_questions': parsed.suggested_questions,
        }
        if parsed.conversation_title:
            metadata['conversation_title'] = parsed.conversation_title
        return LLMResponse(content=parsed.answer, metadata=metadata)
