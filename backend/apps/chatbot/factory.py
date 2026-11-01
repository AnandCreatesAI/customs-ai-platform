from llm_gateway import LLMGateway
from llm_gateway.providers.gemini import GeminiLLMProvider

from apps.chatbot.services import ChatbotService


def get_chatbot_service(*, llm_gateway: LLMGateway | None = None) -> ChatbotService:
    """Composition root for ChatbotService with the Gemini-backed LLM gateway."""
    gateway = llm_gateway if llm_gateway is not None else LLMGateway(GeminiLLMProvider())
    return ChatbotService(gateway)
