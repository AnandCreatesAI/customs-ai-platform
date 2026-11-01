from copy import deepcopy
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.chatbot.services import ChatbotService
from apps.conversations.models import Conversation, Message, MessageRole
from apps.conversations.persistence import MessagePersistenceError
from apps.model_management.models import BusinessModel, BusinessModelKey
from llm_gateway import LLMGateway, LLMGatewayError, LLMResponse

User = get_user_model()

URL = '/api/v1/chatbot/messages/'

HANDLER_PROMPT_FRAGMENTS = {
    'user': 'User Model assistant',
    'ebooks': 'eBooks Model assistant',
    'employee': 'Employee Model assistant',
    'hs_code': 'HS Code Model assistant',
}


def seed_active_business_models() -> None:
    for key, label in (
        (BusinessModelKey.USER, 'User Model'),
        (BusinessModelKey.EBOOKS, 'eBooks Model'),
        (BusinessModelKey.EMPLOYEE, 'Employee Model'),
        (BusinessModelKey.HS_CODE, 'HS Code Model'),
    ):
        BusinessModel.objects.update_or_create(
            key=key,
            defaults={'name': label, 'description': '', 'is_active': True},
        )


class ChatbotAPITestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='chat@example.com',
            password='secure-pass-123',
        )
        self.client = APIClient()
        seed_active_business_models()
        self.mock_gateway = MagicMock(spec=LLMGateway)
        self.mock_gateway.provider_name = 'gemini'
        self.mock_gateway.model_name = 'gemini-3.5-flash-lite'
        self.mock_gateway.generate.return_value = LLMResponse(
            content='Generated assistant response',
            metadata={'provider': 'gemini', 'model': 'gemini-3.5-flash-lite'},
        )

    def _post_message(self, payload: dict):
        return self.client.post(URL, payload, format='json')

    def _authenticated_post(self, payload: dict):
        self.client.force_authenticate(user=self.user)
        return self._post_message(payload)


class ChatbotMessageAPITests(ChatbotAPITestBase):
    @patch('apps.chatbot.views.get_chatbot_service')
    def test_authenticated_user_model_request(self, mock_get_service):
        mock_get_service.return_value = ChatbotService(self.mock_gateway)
        response = self._authenticated_post(
            {'model_key': 'user', 'message': 'Explain the customs declaration process.'},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['success'])
        self.assertEqual(body['model_key'], 'user')
        self.assertEqual(body['provider'], 'gemini')
        self.assertEqual(body['model'], 'gemini-3.5-flash-lite')
        self.assertEqual(body['response'], 'Generated assistant response')
        self.assertIn('conversation_id', body)
        self.assertIn('assistant_message_id', body)
        self.assertEqual(Conversation.objects.filter(user=self.user).count(), 1)
        conversation = Conversation.objects.get(user=self.user)
        self.assertEqual(str(conversation.id), body['conversation_id'])
        self.assertEqual(conversation.messages.filter(role=MessageRole.USER).count(), 1)
        self.assertEqual(conversation.messages.filter(role=MessageRole.ASSISTANT).count(), 1)
        self.mock_gateway.generate.assert_called_once()
        request = self.mock_gateway.generate.call_args.args[0]
        self.assertIn(HANDLER_PROMPT_FRAGMENTS['user'], request.system_prompt)
        self.assertEqual(request.prompt, 'Explain the customs declaration process.')

    @patch('apps.chatbot.views.get_chatbot_service')
    def test_authenticated_ebooks_model_request(self, mock_get_service):
        mock_get_service.return_value = ChatbotService(self.mock_gateway)
        response = self._authenticated_post({'model_key': 'ebooks', 'message': 'Find a guide.'})
        self.assertEqual(response.status_code, 200)
        request = self.mock_gateway.generate.call_args.args[0]
        self.assertIn(HANDLER_PROMPT_FRAGMENTS['ebooks'], request.system_prompt)

    @patch('apps.chatbot.views.get_chatbot_service')
    def test_authenticated_employee_model_request(self, mock_get_service):
        mock_get_service.return_value = ChatbotService(self.mock_gateway)
        response = self._authenticated_post({'model_key': 'employee', 'message': 'Internal workflow?'})
        self.assertEqual(response.status_code, 200)
        request = self.mock_gateway.generate.call_args.args[0]
        self.assertIn(HANDLER_PROMPT_FRAGMENTS['employee'], request.system_prompt)

    @patch('apps.chatbot.views.get_chatbot_service')
    def test_authenticated_hs_code_model_request(self, mock_get_service):
        mock_get_service.return_value = ChatbotService(self.mock_gateway)
        response = self._authenticated_post({'model_key': 'hs_code', 'message': 'Classify goods.'})
        self.assertEqual(response.status_code, 200)
        request = self.mock_gateway.generate.call_args.args[0]
        self.assertIn(HANDLER_PROMPT_FRAGMENTS['hs_code'], request.system_prompt)

    def test_unauthenticated_request_rejected(self):
        response = self._post_message({'model_key': 'user', 'message': 'Hello'})
        self.assertEqual(response.status_code, 401)

    def test_missing_message_rejected(self):
        response = self._authenticated_post({'model_key': 'user'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('message', response.json())

    def test_empty_message_rejected(self):
        response = self._authenticated_post({'model_key': 'user', 'message': '   '})
        self.assertEqual(response.status_code, 400)
        self.assertIn('message', response.json())

    def test_invalid_model_key_rejected(self):
        response = self._authenticated_post({'model_key': 'invalid', 'message': 'Hello'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('model_key', response.json())

    def test_inactive_business_model_rejected(self):
        BusinessModel.objects.filter(key=BusinessModelKey.USER).update(is_active=False)
        response = self._authenticated_post({'model_key': 'user', 'message': 'Hello'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('model_key', response.json())

    def test_missing_business_model_record_rejected(self):
        BusinessModel.objects.filter(key=BusinessModelKey.USER).delete()
        response = self._authenticated_post({'model_key': 'user', 'message': 'Hello'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('model_key', response.json())

    @patch('apps.chatbot.views.get_chatbot_service')
    def test_gemini_503_returns_service_unavailable(self, mock_get_service):
        self.mock_gateway.generate.side_effect = LLMGatewayError('Gemini model temporarily unavailable')
        mock_get_service.return_value = ChatbotService(self.mock_gateway)
        response = self._authenticated_post({'model_key': 'user', 'message': 'Hello'})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['detail'], 'Gemini model temporarily unavailable')

    @patch('apps.chatbot.views.get_chatbot_service')
    def test_gemini_504_returns_gateway_timeout(self, mock_get_service):
        self.mock_gateway.generate.side_effect = LLMGatewayError('Gemini generation deadline exceeded')
        mock_get_service.return_value = ChatbotService(self.mock_gateway)
        response = self._authenticated_post({'model_key': 'user', 'message': 'Hello'})
        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.json()['detail'], 'Gemini generation deadline exceeded')

    @patch('apps.chatbot.views.get_chatbot_service')
    def test_unexpected_provider_failure_returns_bad_gateway(self, mock_get_service):
        self.mock_gateway.generate.side_effect = LLMGatewayError(
            "LLM generation failed via provider 'gemini'",
        )
        mock_get_service.return_value = ChatbotService(self.mock_gateway)
        response = self._authenticated_post({'model_key': 'user', 'message': 'Hello'})
        self.assertEqual(response.status_code, 502)

    @patch('apps.chatbot.views.get_chatbot_service')
    def test_successful_response_metadata_from_llm_response(self, mock_get_service):
        self.mock_gateway.generate.return_value = LLMResponse(
            content='Custom text',
            metadata={'provider': 'gemini', 'model': 'gemini-3.5-flash-lite'},
        )
        mock_get_service.return_value = ChatbotService(self.mock_gateway)
        response = self._authenticated_post({'model_key': 'user', 'message': 'Hello'})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['provider'], 'gemini')
        self.assertEqual(body['model'], 'gemini-3.5-flash-lite')
        self.assertEqual(body['response'], 'Custom text')

    def test_inactive_user_receives_forbidden(self):
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        self.client.force_authenticate(user=self.user)
        response = self._post_message({'model_key': 'user', 'message': 'Hello'})
        self.assertEqual(response.status_code, 403)


class ChatbotMessagePersistenceTests(ChatbotAPITestBase):
    @patch('apps.chatbot.views.get_chatbot_service')
    def test_new_conversation_created_when_conversation_id_omitted(self, mock_get_service):
        mock_get_service.return_value = ChatbotService(self.mock_gateway)
        response = self._authenticated_post({'model_key': 'user', 'message': 'First message'})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        conversation = Conversation.objects.get(pk=body['conversation_id'])
        self.assertEqual(conversation.user, self.user)
        self.assertEqual(conversation.business_model.key, 'user')
        self.assertEqual(conversation.messages.count(), 2)

    @patch('apps.chatbot.views.get_chatbot_service')
    def test_existing_conversation_appends_messages(self, mock_get_service):
        mock_get_service.return_value = ChatbotService(self.mock_gateway)
        business_model = BusinessModel.objects.get(key=BusinessModelKey.USER)
        conversation = Conversation.objects.create(
            user=self.user,
            business_model=business_model,
        )
        first = self._authenticated_post(
            {
                'model_key': 'user',
                'message': 'Follow-up',
                'conversation_id': str(conversation.id),
            },
        )
        self.assertEqual(first.status_code, 200)
        conversation.refresh_from_db()
        self.assertEqual(conversation.messages.count(), 2)
        self.assertEqual(
            first.json()['conversation_id'],
            str(conversation.id),
        )

    @patch('apps.chatbot.views.get_chatbot_service')
    def test_other_users_conversation_returns_not_found(self, mock_get_service):
        mock_get_service.return_value = ChatbotService(self.mock_gateway)
        other = User.objects.create_user(
            email='other@example.com',
            password='secure-pass-123',
        )
        business_model = BusinessModel.objects.get(key=BusinessModelKey.USER)
        conversation = Conversation.objects.create(
            user=other,
            business_model=business_model,
        )
        response = self._authenticated_post(
            {
                'model_key': 'user',
                'message': 'Hello',
                'conversation_id': str(conversation.id),
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(conversation.messages.count(), 0)

    @patch('apps.chatbot.views.get_chatbot_service')
    def test_conversation_model_mismatch_rejected(self, mock_get_service):
        mock_get_service.return_value = ChatbotService(self.mock_gateway)
        business_model = BusinessModel.objects.get(key=BusinessModelKey.EBOOKS)
        conversation = Conversation.objects.create(
            user=self.user,
            business_model=business_model,
        )
        response = self._authenticated_post(
            {
                'model_key': 'user',
                'message': 'Hello',
                'conversation_id': str(conversation.id),
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(conversation.messages.count(), 0)

    @patch('apps.chatbot.views.get_chatbot_service')
    def test_inactive_conversation_rejected(self, mock_get_service):
        mock_get_service.return_value = ChatbotService(self.mock_gateway)
        business_model = BusinessModel.objects.get(key=BusinessModelKey.USER)
        conversation = Conversation.objects.create(
            user=self.user,
            business_model=business_model,
            is_active=False,
        )
        response = self._authenticated_post(
            {
                'model_key': 'user',
                'message': 'Hello',
                'conversation_id': str(conversation.id),
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(conversation.messages.count(), 0)

    def test_unknown_conversation_id_rejected(self):
        import uuid

        response = self._authenticated_post(
            {
                'model_key': 'user',
                'message': 'Hello',
                'conversation_id': str(uuid.uuid4()),
            },
        )
        self.assertEqual(response.status_code, 404)

    @patch('apps.chatbot.views.get_chatbot_service')
    def test_llm_failure_preserves_user_message_only(self, mock_get_service):
        self.mock_gateway.generate.side_effect = LLMGatewayError('Gemini model temporarily unavailable')
        mock_get_service.return_value = ChatbotService(self.mock_gateway)
        response = self._authenticated_post({'model_key': 'user', 'message': 'Hello'})
        self.assertEqual(response.status_code, 503)
        conversation = Conversation.objects.get(user=self.user)
        self.assertEqual(conversation.messages.filter(role=MessageRole.USER).count(), 1)
        self.assertEqual(conversation.messages.filter(role=MessageRole.ASSISTANT).count(), 0)

    @patch('apps.chatbot.views.get_chatbot_service')
    def test_assistant_message_stores_provider_metadata(self, mock_get_service):
        mock_get_service.return_value = ChatbotService(self.mock_gateway)
        response = self._authenticated_post({'model_key': 'user', 'message': 'Hello'})
        self.assertEqual(response.status_code, 200)
        assistant = Message.objects.get(pk=response.json()['assistant_message_id'])
        self.assertEqual(assistant.role, MessageRole.ASSISTANT)
        self.assertEqual(assistant.provider_key, 'gemini')
        self.assertEqual(assistant.model_name, 'gemini-3.5-flash-lite')
        self.assertEqual(assistant.content, 'Generated assistant response')


def _strict_throttle_settings():
    rest_framework = deepcopy(settings.REST_FRAMEWORK)
    rest_framework['DEFAULT_THROTTLE_RATES'] = {
        'chatbot_message': '2/minute',
        'conversation_history': '2/minute',
    }
    return {'REST_FRAMEWORK': rest_framework}


class ChatbotReliabilityTests(ChatbotAPITestBase):
    @patch('apps.chatbot.views.get_chatbot_service')
    def test_value_error_after_user_message_persisted(self, mock_get_service):
        service = ChatbotService(self.mock_gateway)
        mock_get_service.return_value = service
        with patch.object(
            ChatbotService,
            'process_message_response',
            side_effect=ValueError('internal handler failure'),
        ):
            response = self._authenticated_post({'model_key': 'user', 'message': 'Hello'})
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body['detail'], 'Unable to complete the assistant response.')
        self.assertIn('conversation_id', body)
        conversation = Conversation.objects.get(pk=body['conversation_id'])
        self.assertEqual(conversation.messages.filter(role=MessageRole.USER).count(), 1)
        self.assertEqual(conversation.messages.filter(role=MessageRole.ASSISTANT).count(), 0)

    @patch('apps.chatbot.views.get_chatbot_service')
    def test_assistant_persistence_failure_does_not_report_success(self, mock_get_service):
        mock_get_service.return_value = ChatbotService(self.mock_gateway)
        with patch(
            'apps.chatbot.views.persist_assistant_message',
            side_effect=MessagePersistenceError('Unable to save assistant message.'),
        ):
            response = self._authenticated_post({'model_key': 'user', 'message': 'Hello'})
        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body['detail'], 'Assistant response could not be saved.')
        self.assertIn('conversation_id', body)
        self.assertNotIn('success', body)
        conversation = Conversation.objects.get(pk=body['conversation_id'])
        self.assertEqual(conversation.messages.filter(role=MessageRole.ASSISTANT).count(), 0)

    @patch('apps.chatbot.views.get_chatbot_service')
    def test_llm_failure_includes_conversation_id(self, mock_get_service):
        self.mock_gateway.generate.side_effect = LLMGatewayError('Gemini model temporarily unavailable')
        mock_get_service.return_value = ChatbotService(self.mock_gateway)
        response = self._authenticated_post({'model_key': 'user', 'message': 'Hello'})
        self.assertEqual(response.status_code, 503)
        self.assertIn('conversation_id', response.json())

    def test_resolve_conversation_locks_existing_row(self):
        from apps.conversations.persistence import resolve_conversation

        business_model = BusinessModel.objects.get(key=BusinessModelKey.USER)
        conversation = Conversation.objects.create(
            user=self.user,
            business_model=business_model,
        )
        with patch('apps.conversations.persistence.Conversation.objects.filter') as mock_filter:
            locked_queryset = MagicMock()
            mock_filter.return_value.select_for_update.return_value = locked_queryset
            locked_queryset.get.return_value = conversation
            resolve_conversation(
                user=self.user,
                business_model=business_model,
                conversation_id=conversation.id,
                lock=True,
            )
        mock_filter.return_value.select_for_update.assert_called_once()

    @patch('apps.chatbot.views.get_chatbot_service')
    def test_sequential_posts_to_same_conversation_persist_both_turns(self, mock_get_service):
        mock_get_service.return_value = ChatbotService(self.mock_gateway)
        business_model = BusinessModel.objects.get(key=BusinessModelKey.USER)
        conversation = Conversation.objects.create(
            user=self.user,
            business_model=business_model,
        )
        for text in ('First', 'Second'):
            response = self._authenticated_post(
                {
                    'model_key': 'user',
                    'message': text,
                    'conversation_id': str(conversation.id),
                },
            )
            self.assertEqual(response.status_code, 200)
        conversation.refresh_from_db()
        self.assertEqual(conversation.messages.filter(role=MessageRole.USER).count(), 2)
        self.assertEqual(conversation.messages.filter(role=MessageRole.ASSISTANT).count(), 2)

    @patch('apps.chatbot.views.get_chatbot_service')
    def test_chatbot_throttling(self, mock_get_service):
        from django.core.cache import cache

        mock_get_service.return_value = ChatbotService(self.mock_gateway)
        with override_settings(**_strict_throttle_settings()):
            cache.clear()
            for _ in range(2):
                response = self._authenticated_post({'model_key': 'user', 'message': 'Hello'})
                self.assertEqual(response.status_code, 200)
            throttled = self._authenticated_post({'model_key': 'user', 'message': 'Hello again'})
            self.assertEqual(throttled.status_code, 429)
