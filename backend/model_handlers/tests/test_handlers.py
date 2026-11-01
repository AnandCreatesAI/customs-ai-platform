from unittest.mock import MagicMock

from django.test import SimpleTestCase

from llm_gateway import LLMGateway, LLMRequest, LLMResponse
from model_handlers.ebooks_model import EbooksModelHandler
from model_handlers.employee_model import EmployeeModelHandler
from model_handlers.hs_code_model import HsCodeModelHandler
from model_handlers.registry import get_model_handler
from model_handlers.user_model import UserModelHandler


class ModelHandlerTests(SimpleTestCase):
    HANDLER_CASES = (
        (UserModelHandler, 'user', 'User Model assistant'),
        (EbooksModelHandler, 'ebooks', 'eBooks Model assistant'),
        (EmployeeModelHandler, 'employee', 'Employee Model assistant'),
        (HsCodeModelHandler, 'hs_code', 'HS Code Model assistant'),
    )

    def test_handler_initialization_with_gateway(self):
        gateway = LLMGateway(MagicMock())
        for handler_class, model_key, _ in self.HANDLER_CASES:
            handler = handler_class(gateway)
            self.assertIs(handler.llm_gateway, gateway)
            self.assertEqual(handler.model_key, model_key)

    def test_each_handler_system_prompt(self):
        gateway = LLMGateway(MagicMock())
        for handler_class, _, prompt_fragment in self.HANDLER_CASES:
            handler = handler_class(gateway)
            self.assertIn(prompt_fragment, handler.build_system_prompt())

    def test_handler_calls_gateway_with_expected_request(self):
        gateway = MagicMock(spec=LLMGateway)
        gateway.generate.return_value = LLMResponse(content='assistant reply')

        handler = UserModelHandler(gateway)
        result = handler.handle('What is customs?', context={'session_id': 'abc'})

        gateway.generate.assert_called_once()
        request = gateway.generate.call_args.args[0]
        self.assertIsInstance(request, LLMRequest)
        self.assertEqual(request.prompt, 'What is customs?')
        self.assertIn('User Model assistant', request.system_prompt)
        self.assertEqual(request.metadata['model_key'], 'user')
        self.assertEqual(request.metadata['context'], {'session_id': 'abc'})
        self.assertEqual(result, 'assistant reply')

    def test_all_handlers_return_gateway_content(self):
        gateway = MagicMock(spec=LLMGateway)
        gateway.generate.return_value = LLMResponse(content='shared-response')

        for model_key in ('user', 'ebooks', 'employee', 'hs_code'):
            handler = get_model_handler(model_key, gateway)
            self.assertEqual(handler.handle('Hello'), 'shared-response')
