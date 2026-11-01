from abc import ABC, abstractmethod
from typing import Any

from llm_gateway import LLMGateway, LLMRequest, LLMResponse


class BaseModelHandler(ABC):
    """Base class for domain-specific AI model handlers."""

    model_key: str

    def __init__(self, llm_gateway: LLMGateway) -> None:
        self.llm_gateway = llm_gateway

    @abstractmethod
    def build_system_prompt(self) -> str:
        raise NotImplementedError

    def generate_response(
        self,
        user_message: str,
        context: dict[str, Any] | None = None,
    ) -> LLMResponse:
        request = LLMRequest(
            prompt=user_message,
            system_prompt=self.build_system_prompt(),
            metadata={'model_key': self.model_key, 'context': context or {}},
        )
        return self.llm_gateway.generate(request)

    def handle(self, user_message: str, context: dict[str, Any] | None = None) -> str:
        return self.generate_response(user_message, context).content
