from model_handlers.base import BaseModelHandler


class EmployeeModelHandler(BaseModelHandler):
    model_key = 'employee'

    def build_system_prompt(self) -> str:
        return (
            'You are the Employee Model assistant for internal staff. '
            'Support operational and procedural customs workflows.'
        )
