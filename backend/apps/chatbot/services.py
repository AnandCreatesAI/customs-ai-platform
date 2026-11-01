from typing import Any

from llm_gateway import LLMGateway, LLMResponse
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
        return self.process_message_response(model_key, user_message, context).content

    def process_message_response(
        self,
        model_key: str,
        user_message: str,
        context: dict[str, Any] | None = None,
    ) -> LLMResponse:
        handler = get_model_handler(model_key, self._llm_gateway)
        return handler.generate_response(user_message, context)
