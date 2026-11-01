from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.chatbot.services import ChatbotService
from llm_gateway import LLMGateway, LLMGatewayError, LLMResponse
from llm_gateway.providers.stub import StubLLMProvider
from model_handlers.registry import MODEL_HANDLER_CLASSES


class ChatbotServiceTests(SimpleTestCase):
    def setUp(self):
        self.service = ChatbotService(LLMGateway(StubLLMProvider()))

    def test_process_message_for_all_supported_model_keys(self):
        for model_key in sorted(MODEL_HANDLER_CLASSES.keys()):
            reply = self.service.process_message(model_key, f'Hello from {model_key}')
            self.assertIn('[stub:stub]', reply)
            self.assertIn(f'Hello from {model_key}', reply)

    def test_invalid_model_key_handling(self):
        with self.assertRaisesMessage(ValueError, 'Unknown model handler: not-a-model'):
            self.service.process_message('not-a-model', 'Hello')

    def test_correct_handler_selection(self):
        gateway = MagicMock(spec=LLMGateway)
        gateway.generate.return_value = LLMResponse(content='ok')
        service = ChatbotService(gateway)

        service.process_message('hs_code', 'Classify goods')
        request = gateway.generate.call_args.args[0]
        self.assertEqual(request.metadata['model_key'], 'hs_code')
        self.assertIn('HS Code Model assistant', request.system_prompt)

    def test_context_forwarding(self):
        gateway = MagicMock(spec=LLMGateway)
        gateway.generate.return_value = LLMResponse(content='ok')
        service = ChatbotService(gateway)

        service.process_message('user', 'Question', context={'foo': 'bar'})
        request = gateway.generate.call_args.args[0]
        self.assertEqual(request.metadata['context'], {'foo': 'bar'})

    def test_gateway_errors_propagate(self):
        gateway = MagicMock(spec=LLMGateway)
        gateway.generate.side_effect = LLMGatewayError('generation failed')
        service = ChatbotService(gateway)

        with self.assertRaises(LLMGatewayError):
            service.process_message('user', 'Hello')

    def test_requires_gateway_dependency_injection(self):
        with self.assertRaises(ValueError):
            ChatbotService(None)

    def test_supported_model_keys_matches_registry(self):
        self.assertEqual(
            self.service.supported_model_keys(),
            sorted(MODEL_HANDLER_CLASSES.keys()),
        )
