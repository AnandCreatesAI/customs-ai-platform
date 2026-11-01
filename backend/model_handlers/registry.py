from typing import Type

from llm_gateway import LLMGateway
from model_handlers.base import BaseModelHandler
from model_handlers.ebooks_model import EbooksModelHandler
from model_handlers.employee_model import EmployeeModelHandler
from model_handlers.hs_code_model import HsCodeModelHandler
from model_handlers.user_model import UserModelHandler

MODEL_HANDLER_CLASSES: dict[str, Type[BaseModelHandler]] = {
    UserModelHandler.model_key: UserModelHandler,
    EbooksModelHandler.model_key: EbooksModelHandler,
    EmployeeModelHandler.model_key: EmployeeModelHandler,
    HsCodeModelHandler.model_key: HsCodeModelHandler,
}


def get_model_handler(model_key: str, llm_gateway: LLMGateway) -> BaseModelHandler:
    try:
        handler_class = MODEL_HANDLER_CLASSES[model_key]
    except KeyError as exc:
        raise ValueError(f'Unknown model handler: {model_key}') from exc
    return handler_class(llm_gateway)
