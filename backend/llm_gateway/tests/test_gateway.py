from unittest.mock import MagicMock

from django.test import SimpleTestCase

from llm_gateway import LLMGateway, LLMGatewayError, LLMRequest, LLMResponse
from llm_gateway.providers.stub import StubLLMProvider


class LLMRequestResponseTests(SimpleTestCase):
    def test_llm_request_fields(self):
        request = LLMRequest(
            prompt='Hello',
            system_prompt='System',
            metadata={'key': 'value'},
        )
        self.assertEqual(request.prompt, 'Hello')
        self.assertEqual(request.system_prompt, 'System')
        self.assertEqual(request.metadata['key'], 'value')

    def test_llm_response_fields(self):
        response = LLMResponse(content='Reply', metadata={'provider': 'stub'})
        self.assertEqual(response.content, 'Reply')
        self.assertEqual(response.metadata['provider'], 'stub')


class LLMGatewayTests(SimpleTestCase):
    def test_successful_request_with_stub_provider(self):
        gateway = LLMGateway(StubLLMProvider())
        response = gateway.generate(LLMRequest(prompt='Customs question'))
        self.assertIn('[stub:stub]', response.content)
        self.assertIn('Customs question', response.content)

    def test_provider_invocation(self):
        provider = MagicMock()
        provider.provider_name = 'mock'
        provider.generate.return_value = LLMResponse(content='mocked')
        gateway = LLMGateway(provider)

        request = LLMRequest(prompt='Test prompt', system_prompt='System')
        response = gateway.generate(request)

        provider.generate.assert_called_once_with(request)
        self.assertEqual(response.content, 'mocked')

    def test_empty_prompt_rejected(self):
        gateway = LLMGateway(StubLLMProvider())
        with self.assertRaises(ValueError):
            gateway.generate(LLMRequest(prompt=''))
        with self.assertRaises(ValueError):
            gateway.generate(LLMRequest(prompt='   '))

    def test_none_provider_rejected(self):
        with self.assertRaises(ValueError):
            LLMGateway(None)

    def test_provider_exception_wrapped_as_gateway_error(self):
        provider = MagicMock()
        provider.provider_name = 'failing'
        provider.generate.side_effect = RuntimeError('provider failed')
        gateway = LLMGateway(provider)

        with self.assertRaises(LLMGatewayError):
            gateway.generate(LLMRequest(prompt='Hello'))

    def test_gateway_error_is_reraised(self):
        provider = MagicMock()
        provider.provider_name = 'failing'
        provider.generate.side_effect = LLMGatewayError('already wrapped')
        gateway = LLMGateway(provider)

        with self.assertRaises(LLMGatewayError):
            gateway.generate(LLMRequest(prompt='Hello'))
