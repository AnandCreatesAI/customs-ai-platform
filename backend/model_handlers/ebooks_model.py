from model_handlers.base import BaseModelHandler


class EbooksModelHandler(BaseModelHandler):
    model_key = 'ebooks'

    def build_system_prompt(self) -> str:
        return (
            'You are the eBooks Model assistant. '
            'Answer questions using customs eBook and publication knowledge.'
        )

    def build_rag_instructions(self) -> str:
        return (
            'Focus on customs eBooks and publications in the reference blocks. '
            'Tie explanations to cited passages and distinguish publication text from general commentary.'
        )
