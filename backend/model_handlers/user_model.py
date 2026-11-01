from model_handlers.base import BaseModelHandler


class UserModelHandler(BaseModelHandler):
    model_key = 'user'

    def build_system_prompt(self) -> str:
        return (
            'You are the User Model assistant for the customs AI platform. '
            'Help end users with general customs-related questions.'
        )
