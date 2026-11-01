from unittest.mock import MagicMock, patch

import httpx
from django.test import SimpleTestCase
from google.genai._interactions import (
    APIError,
    AuthenticationError,
    InternalServerError,
    NotFoundError,
    RateLimitError,
)
from google.genai._interactions import APITimeoutError as InteractionsAPITimeoutError

from llm_gateway import LLMGateway, LLMGatewayError, LLMRequest
from llm_gateway.providers.gemini import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_THINKING_LEVEL,
    GeminiLLMProvider,
)


def _completed_interaction(text: str) -> MagicMock:
    interaction = MagicMock()
    interaction.status = 'completed'
    interaction.output_text = text
    interaction.steps = None
    interaction.outputs = None
    return interaction


class GeminiLLMProviderTests(SimpleTestCase):
    def test_missing_api_key_rejected(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesMessage(LLMGatewayError, 'GEMINI_API_KEY is not configured'):
                GeminiLLMProvider()

    def test_initialization_with_explicit_credentials(self):
        provider = GeminiLLMProvider(api_key='test-key', model='gemini-3.5-flash-lite')
        self.assertEqual(provider.model_name, 'gemini-3.5-flash-lite')

    def test_default_model_from_environment(self):
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key', 'GEMINI_MODEL': 'custom-model'}):
            provider = GeminiLLMProvider()
        self.assertEqual(provider.model_name, 'custom-model')

    def test_default_model_fallback(self):
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key', 'GEMINI_MODEL': ''}, clear=False):
            provider = GeminiLLMProvider(model=None)
        self.assertEqual(provider.model_name, DEFAULT_GEMINI_MODEL)
        self.assertEqual(DEFAULT_GEMINI_MODEL, 'gemini-3.5-flash-lite')

    def test_extracts_text_from_output_text_field(self):
        interaction = MagicMock()
        interaction.status = 'completed'
        interaction.output_text = 'SDK helper text'
        interaction.steps = None
        interaction.outputs = None
        self.assertEqual(GeminiLLMProvider._extract_interaction_text(interaction), 'SDK helper text')

    def test_extracts_text_from_steps_when_output_text_empty(self):
        block = MagicMock()
        block.type = 'text'
        block.text = 'From steps'
        step = MagicMock()
        step.type = 'model_output'
        step.content = [block]
        interaction = MagicMock()
        interaction.status = 'completed'
        interaction.output_text = ''
        interaction.steps = [step]
        interaction.outputs = None
        self.assertEqual(GeminiLLMProvider._extract_interaction_text(interaction), 'From steps')

    @patch('llm_gateway.providers.gemini.genai.Client')
    def test_system_instruction_and_user_prompt_mapping(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.interactions.create.return_value = _completed_interaction('Gemini reply')
        mock_client_cls.return_value = mock_client

        provider = GeminiLLMProvider(api_key='test-key', model='gemini-3.5-flash-lite', client=mock_client)
        response = provider.generate(
            LLMRequest(prompt='User question', system_prompt='System instruction'),
        )

        mock_client.interactions.create.assert_called_once()
        kwargs = mock_client.interactions.create.call_args.kwargs
        self.assertEqual(kwargs['model'], 'gemini-3.5-flash-lite')
        self.assertEqual(kwargs['input'], 'User question')
        self.assertEqual(kwargs['system_instruction'], 'System instruction')
        self.assertEqual(kwargs['generation_config'], {'thinking_level': DEFAULT_THINKING_LEVEL})
        self.assertEqual(response.content, 'Gemini reply')
        self.assertEqual(response.metadata['provider'], 'gemini')
        self.assertEqual(response.metadata['model'], 'gemini-3.5-flash-lite')

    @patch('llm_gateway.providers.gemini.genai.Client')
    def test_empty_response_rejected(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.interactions.create.return_value = _completed_interaction('   ')
        mock_client_cls.return_value = mock_client

        provider = GeminiLLMProvider(api_key='test-key', client=mock_client)
        with self.assertRaisesMessage(LLMGatewayError, 'Gemini returned an empty response'):
            provider.generate(LLMRequest(prompt='Hello'))

    @patch('llm_gateway.providers.gemini.genai.Client')
    def test_authentication_error_mapping(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_client.interactions.create.side_effect = AuthenticationError(
            'invalid',
            response=mock_response,
            body={'error': {'message': 'invalid'}},
        )
        mock_client_cls.return_value = mock_client

        provider = GeminiLLMProvider(api_key='bad-key', client=mock_client)
        with self.assertRaisesMessage(LLMGatewayError, 'Gemini authentication failed'):
            provider.generate(LLMRequest(prompt='Hello'))

    @patch('llm_gateway.providers.gemini.genai.Client')
    def test_rate_limit_error_mapping(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_client.interactions.create.side_effect = RateLimitError(
            'rate limit',
            response=mock_response,
            body={'error': {'message': 'rate limit'}},
        )
        mock_client_cls.return_value = mock_client

        provider = GeminiLLMProvider(api_key='test-key', client=mock_client)
        with self.assertRaisesMessage(LLMGatewayError, 'Gemini quota or rate limit exceeded'):
            provider.generate(LLMRequest(prompt='Hello'))

    @patch('llm_gateway.providers.gemini.genai.Client')
    def test_model_unavailable_error_mapping(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.interactions.create.side_effect = NotFoundError(
            'not found',
            response=mock_response,
            body={'error': {'message': 'model unavailable'}},
        )
        mock_client_cls.return_value = mock_client

        provider = GeminiLLMProvider(api_key='test-key', client=mock_client)
        with self.assertRaisesMessage(LLMGatewayError, 'Gemini model unavailable'):
            provider.generate(LLMRequest(prompt='Hello'))

    @patch('llm_gateway.providers.gemini.genai.Client')
    def test_service_unavailable_error_mapping(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_client.interactions.create.side_effect = InternalServerError(
            'unavailable',
            response=mock_response,
            body={'error': {'message': 'unavailable'}},
        )
        mock_client_cls.return_value = mock_client

        provider = GeminiLLMProvider(api_key='test-key', client=mock_client)
        with self.assertRaisesMessage(LLMGatewayError, 'Gemini model temporarily unavailable'):
            provider.generate(LLMRequest(prompt='Hello'))

    @patch('llm_gateway.providers.gemini.genai.Client')
    def test_deadline_exceeded_error_mapping(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 504
        mock_client.interactions.create.side_effect = APIError.generate(
            504,
            {'error': {'code': 'deadline_exceeded'}},
            'deadline exceeded',
            mock_response,
        )
        mock_client_cls.return_value = mock_client

        provider = GeminiLLMProvider(api_key='test-key', client=mock_client)
        with self.assertRaisesMessage(LLMGatewayError, 'Gemini generation deadline exceeded'):
            provider.generate(LLMRequest(prompt='Hello'))

    def test_map_http_status_deadline_exceeded(self):
        err = GeminiLLMProvider._map_http_status(504)
        self.assertEqual(str(err), 'Gemini generation deadline exceeded')

    @patch('llm_gateway.providers.gemini.genai.Client')
    def test_timeout_error_mapping(self, mock_client_cls):
        mock_client = MagicMock()
        mock_request = MagicMock()
        mock_client.interactions.create.side_effect = InteractionsAPITimeoutError(request=mock_request)
        mock_client_cls.return_value = mock_client

        provider = GeminiLLMProvider(api_key='test-key', client=mock_client)
        with self.assertRaisesMessage(LLMGatewayError, 'Gemini request timed out'):
            provider.generate(LLMRequest(prompt='Hello'))

    @patch('llm_gateway.providers.gemini.genai.Client')
    def test_network_timeout_via_httpx(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.interactions.create.side_effect = httpx.TimeoutException('timed out')
        mock_client_cls.return_value = mock_client

        provider = GeminiLLMProvider(api_key='test-key', client=mock_client)
        with self.assertRaisesMessage(LLMGatewayError, 'Gemini request timed out'):
            provider.generate(LLMRequest(prompt='Hello'))

    @patch('llm_gateway.providers.gemini.genai.Client')
    def test_gateway_propagates_gemini_provider_errors(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_client.interactions.create.side_effect = InternalServerError(
            'unavailable',
            response=mock_response,
            body={'error': {'message': 'unavailable'}},
        )
        mock_client_cls.return_value = mock_client

        gateway = LLMGateway(GeminiLLMProvider(api_key='test-key', client=mock_client))
        with self.assertRaises(LLMGatewayError):
            gateway.generate(LLMRequest(prompt='Hello'))
