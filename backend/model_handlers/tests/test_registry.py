from django.test import SimpleTestCase

from llm_gateway import LLMGateway
from llm_gateway.providers.stub import StubLLMProvider
from model_handlers.registry import MODEL_HANDLER_CLASSES, get_model_handler


class ModelHandlerRegistryTests(SimpleTestCase):
    def setUp(self):
        self.gateway = LLMGateway(StubLLMProvider())

    def test_registry_contains_four_handlers(self):
        self.assertEqual(
            set(MODEL_HANDLER_CLASSES.keys()),
            {'user', 'ebooks', 'employee', 'hs_code'},
        )

    def test_get_model_handler_returns_correct_types(self):
        for key in MODEL_HANDLER_CLASSES:
            handler = get_model_handler(key, self.gateway)
            self.assertEqual(handler.model_key, key)
            self.assertIs(handler.llm_gateway, self.gateway)

    def test_unknown_model_key_rejected(self):
        with self.assertRaisesMessage(ValueError, 'Unknown model handler: invalid'):
            get_model_handler('invalid', self.gateway)
