from model_handlers.base import BaseModelHandler


class UserModelHandler(BaseModelHandler):
    model_key = 'user'

    def build_system_prompt(self) -> str:
        return (
            'You are the User Model assistant for the customs AI platform. '
            'Help end users with general customs-related questions.'
        )

    def build_rag_instructions(self) -> str:
        return (
            'Audience: end users. Prefer clear, plain language. '
            'When indexed publications support an answer, cite them and avoid internal-only jargon.'
        )
