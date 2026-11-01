from model_handlers.base import BaseModelHandler


class HsCodeModelHandler(BaseModelHandler):
    model_key = 'hs_code'

    def build_system_prompt(self) -> str:
        return (
            'You are the HS Code Model assistant. '
            'Help classify goods and interpret harmonized system codes.'
        )
