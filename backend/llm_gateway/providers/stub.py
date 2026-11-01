from llm_gateway.interfaces import LLMProvider, LLMRequest, LLMResponse


class StubLLMProvider(LLMProvider):
    """Local stub provider for development and wiring tests (no external API calls)."""

    provider_name = 'stub'

    def generate(self, request: LLMRequest) -> LLMResponse:
        preview = request.prompt.strip()[:120]
        content = f'[stub:{self.provider_name}] Received: {preview}'
        return LLMResponse(content=content, metadata={'provider': self.provider_name})
