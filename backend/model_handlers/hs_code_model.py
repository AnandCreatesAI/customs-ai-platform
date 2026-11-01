from model_handlers.base import BaseModelHandler


class HsCodeModelHandler(BaseModelHandler):
    model_key = 'hs_code'

    def build_system_prompt(self) -> str:
        return (
            'You are the HS Code Model assistant. '
            'Help classify goods and interpret harmonized system codes.'
        )

    def build_rag_instructions(self) -> str:
        return (
            'HS classification claims must be supported by cited reference blocks when available. '
            'Do not invent tariff lines or legal notes not present in the sources.'
        )
