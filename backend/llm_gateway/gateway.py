from llm_gateway.interfaces import LLMProvider, LLMRequest, LLMResponse


class LLMGatewayError(Exception):
    """Raised when the gateway cannot complete a provider request."""


class LLMGateway:
    """Central entry point for all model handlers to call LLM providers."""

    def __init__(self, provider: LLMProvider) -> None:
        if provider is None:
            raise ValueError('LLM provider is required')
        self._provider = provider

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name

    @property
    def model_name(self) -> str | None:
        return getattr(self._provider, 'model_name', None)

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not request.prompt or not request.prompt.strip():
            raise ValueError('LLM request prompt cannot be empty')
        try:
            return self._provider.generate(request)
        except LLMGatewayError:
            raise
        except Exception as exc:
            raise LLMGatewayError(
                f'LLM generation failed via provider {self._provider.provider_name!r}'
            ) from exc
