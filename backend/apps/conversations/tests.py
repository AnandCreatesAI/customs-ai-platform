import uuid
from copy import deepcopy
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.conversations.models import Conversation, Message, MessageRole
from apps.model_management.models import BusinessModel, BusinessModelKey

User = get_user_model()


class ConversationsTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='owner@example.com',
            password='secure-pass-123',
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='secure-pass-123',
        )
        self.business_model = BusinessModel.objects.create(
            key=BusinessModelKey.USER,
            name='User Model',
        )


class ConversationModelTests(ConversationsTestBase):
    def test_create_conversation_for_user(self):
        conversation = Conversation.objects.create(
            user=self.user,
            business_model=self.business_model,
            title='Customs help',
        )
        self.assertEqual(conversation.user, self.user)
        self.assertEqual(conversation.title, 'Customs help')

    def test_associates_existing_business_model(self):
        conversation = Conversation.objects.create(
            user=self.user,
            business_model=self.business_model,
        )
        self.assertEqual(conversation.business_model.key, BusinessModelKey.USER)

    def test_uuid_primary_key(self):
        conversation = Conversation.objects.create(
            user=self.user,
            business_model=self.business_model,
        )
        self.assertIsInstance(conversation.id, uuid.UUID)

    def test_default_active_status(self):
        conversation = Conversation.objects.create(
            user=self.user,
            business_model=self.business_model,
        )
        self.assertTrue(conversation.is_active)

    def test_user_ownership(self):
        conversation = Conversation.objects.create(
            user=self.user,
            business_model=self.business_model,
        )
        self.assertIn(conversation, self.user.conversations.all())

    def test_business_model_protect_on_delete(self):
        conversation = Conversation.objects.create(
            user=self.user,
            business_model=self.business_model,
        )
        self.assertIsNotNone(conversation.id)
        with self.assertRaises(ProtectedError):
            self.business_model.delete()

    def test_user_deletion_cascades_conversations(self):
        conversation = Conversation.objects.create(
            user=self.user,
            business_model=self.business_model,
        )
        conversation_id = conversation.id
        self.user.delete()
        self.assertFalse(Conversation.objects.filter(id=conversation_id).exists())

    def test_ordering_and_indexes_defined(self):
        conversation = Conversation.objects.create(
            user=self.user,
            business_model=self.business_model,
        )
        index_fields = {
            tuple(index.fields)
            for index in Conversation._meta.indexes
        }
        self.assertIn(('user', 'updated_at'), index_fields)
        self.assertIn(('business_model', 'created_at'), index_fields)
        self.assertEqual(Conversation._meta.ordering, ['-updated_at'])
        self.assertIsNotNone(conversation)


class MessageModelTests(ConversationsTestBase):
    def setUp(self):
        super().setUp()
        self.conversation = Conversation.objects.create(
            user=self.user,
            business_model=self.business_model,
        )

    def test_create_user_message(self):
        message = Message.objects.create(
            conversation=self.conversation,
            role=MessageRole.USER,
            content='What is HS code classification?',
        )
        self.assertEqual(message.role, MessageRole.USER)

    def test_create_assistant_message(self):
        message = Message.objects.create(
            conversation=self.conversation,
            role=MessageRole.ASSISTANT,
            content='HS codes classify traded goods.',
            provider_key='gemini',
            model_name='gemini-model-placeholder',
        )
        self.assertEqual(message.role, MessageRole.ASSISTANT)

    def test_create_system_message(self):
        message = Message.objects.create(
            conversation=self.conversation,
            role=MessageRole.SYSTEM,
            content='You are a helpful assistant.',
        )
        self.assertEqual(message.role, MessageRole.SYSTEM)

    def test_conversation_relationship(self):
        message = Message.objects.create(
            conversation=self.conversation,
            role=MessageRole.USER,
            content='Hello',
        )
        self.assertEqual(message.conversation, self.conversation)
        self.assertEqual(self.conversation.messages.count(), 1)

    def test_conversation_deletion_cascades_messages(self):
        message = Message.objects.create(
            conversation=self.conversation,
            role=MessageRole.USER,
            content='Hello',
        )
        message_id = message.id
        self.conversation.delete()
        self.assertFalse(Message.objects.filter(id=message_id).exists())

    def test_optional_provider_and_model_values(self):
        message = Message.objects.create(
            conversation=self.conversation,
            role=MessageRole.USER,
            content='No provider metadata',
        )
        self.assertEqual(message.provider_key, '')
        self.assertEqual(message.model_name, '')

    def test_nullable_token_fields(self):
        message = Message.objects.create(
            conversation=self.conversation,
            role=MessageRole.ASSISTANT,
            content='Response',
        )
        self.assertIsNone(message.prompt_tokens)
        self.assertIsNone(message.completion_tokens)
        self.assertIsNone(message.total_tokens)

    def test_metadata_json_behavior(self):
        message = Message(
            conversation=self.conversation,
            role=MessageRole.ASSISTANT,
            content='Response',
            metadata={'handler_key': 'user', 'latency_ms': 120},
        )
        message.full_clean()
        message.save()
        message.refresh_from_db()
        self.assertEqual(message.metadata['latency_ms'], 120)

    def test_metadata_rejects_secret_like_keys(self):
        message = Message(
            conversation=self.conversation,
            role=MessageRole.ASSISTANT,
            content='Response',
            metadata={'api_key': 'must-not-store'},
        )
        with self.assertRaises(ValidationError):
            message.full_clean()

    def test_uuid_primary_key(self):
        message = Message.objects.create(
            conversation=self.conversation,
            role=MessageRole.USER,
            content='Hello',
        )
        self.assertIsInstance(message.id, uuid.UUID)

    def test_message_ordering(self):
        first = Message.objects.create(
            conversation=self.conversation,
            role=MessageRole.USER,
            content='First',
        )
        second = Message.objects.create(
            conversation=self.conversation,
            role=MessageRole.ASSISTANT,
            content='Second',
        )
        ordered = list(self.conversation.messages.all())
        self.assertEqual(ordered, [first, second])


class ConversationDataIsolationTests(ConversationsTestBase):
    def test_users_own_separate_conversations(self):
        conversation_a = Conversation.objects.create(
            user=self.user,
            business_model=self.business_model,
            title='User A thread',
        )
        conversation_b = Conversation.objects.create(
            user=self.other_user,
            business_model=self.business_model,
            title='User B thread',
        )

        self.assertEqual(self.user.conversations.count(), 1)
        self.assertEqual(self.other_user.conversations.count(), 1)
        self.assertEqual(conversation_a.user.email, 'owner@example.com')
        self.assertEqual(conversation_b.user.email, 'other@example.com')
        self.assertNotEqual(conversation_a.user_id, conversation_b.user_id)


LIST_URL = '/api/v1/conversations/'


def seed_user_business_model() -> BusinessModel:
    business_model, _ = BusinessModel.objects.update_or_create(
        key=BusinessModelKey.USER,
        defaults={'name': 'User Model', 'description': '', 'is_active': True},
    )
    return business_model


class ConversationHistoryAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='history@example.com',
            password='secure-pass-123',
        )
        self.other_user = User.objects.create_user(
            email='other-history@example.com',
            password='secure-pass-123',
        )
        self.client = APIClient()
        self.business_model = seed_user_business_model()

    def test_list_returns_only_authenticated_user_conversations(self):
        own = Conversation.objects.create(user=self.user, business_model=self.business_model)
        Conversation.objects.create(user=self.other_user, business_model=self.business_model)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['count'], 1)
        self.assertEqual(len(body['results']), 1)
        self.assertEqual(body['results'][0]['id'], str(own.id))
        self.assertEqual(body['results'][0]['model_key'], 'user')

    def test_message_list_returns_messages_in_order(self):
        conversation = Conversation.objects.create(user=self.user, business_model=self.business_model)
        Message.objects.create(
            conversation=conversation,
            role=MessageRole.USER,
            content='Question',
        )
        Message.objects.create(
            conversation=conversation,
            role=MessageRole.ASSISTANT,
            content='Answer',
            provider_key='gemini',
            model_name='gemini-3.5-flash-lite',
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'{LIST_URL}{conversation.id}/messages/')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['count'], 2)
        self.assertEqual(body['results'][0]['role'], 'user')
        self.assertEqual(body['results'][1]['role'], 'assistant')

    def test_detail_other_users_conversation_not_found(self):
        conversation = Conversation.objects.create(
            user=self.other_user,
            business_model=self.business_model,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'{LIST_URL}{conversation.id}/')
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_list_rejected(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 401)

    @patch('apps.chatbot.views.get_chatbot_service')
    def test_post_then_get_history(self, mock_get_service):
        from apps.chatbot.services import ChatbotService
        from llm_gateway import LLMResponse

        gateway = MagicMock()
        gateway.provider_name = 'gemini'
        gateway.model_name = 'gemini-3.5-flash-lite'
        gateway.generate.return_value = LLMResponse(
            content='Persisted reply',
            metadata={'provider': 'gemini', 'model': 'gemini-3.5-flash-lite'},
        )
        mock_get_service.return_value = ChatbotService(gateway)

        self.client.force_authenticate(user=self.user)
        post_response = self.client.post(
            '/api/v1/chatbot/messages/',
            {'model_key': 'user', 'message': 'Store this'},
            format='json',
        )
        self.assertEqual(post_response.status_code, 200)
        conversation_id = post_response.json()['conversation_id']

        messages_response = self.client.get(f'{LIST_URL}{conversation_id}/messages/')
        self.assertEqual(messages_response.status_code, 200)
        messages = messages_response.json()['results']
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]['content'], 'Store this')
        self.assertEqual(messages[1]['content'], 'Persisted reply')


class ConversationReliabilityAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='reliability@example.com',
            password='secure-pass-123',
        )
        self.client = APIClient()
        self.business_model = seed_user_business_model()

    def test_conversation_list_pagination_boundaries(self):
        for index in range(25):
            Conversation.objects.create(
                user=self.user,
                business_model=self.business_model,
                title=f'Thread {index}',
            )
        self.client.force_authenticate(user=self.user)
        page_one = self.client.get(LIST_URL, {'page': 1, 'page_size': 20})
        self.assertEqual(page_one.status_code, 200)
        body_one = page_one.json()
        self.assertEqual(body_one['count'], 25)
        self.assertEqual(len(body_one['results']), 20)
        self.assertIsNotNone(body_one['next'])

        page_two = self.client.get(LIST_URL, {'page': 2, 'page_size': 20})
        self.assertEqual(page_two.status_code, 200)
        body_two = page_two.json()
        self.assertEqual(len(body_two['results']), 5)
        self.assertIsNone(body_two['next'])

    def test_empty_message_history_pagination(self):
        conversation = Conversation.objects.create(
            user=self.user,
            business_model=self.business_model,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'{LIST_URL}{conversation.id}/messages/')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['count'], 0)
        self.assertEqual(body['results'], [])

    def test_large_message_history_paginated(self):
        conversation = Conversation.objects.create(
            user=self.user,
            business_model=self.business_model,
        )
        for index in range(45):
            Message.objects.create(
                conversation=conversation,
                role=MessageRole.USER if index % 2 == 0 else MessageRole.ASSISTANT,
                content=f'Message {index}',
            )
        self.client.force_authenticate(user=self.user)
        first_page = self.client.get(
            f'{LIST_URL}{conversation.id}/messages/',
            {'page_size': 20},
        )
        self.assertEqual(first_page.status_code, 200)
        first_body = first_page.json()
        self.assertEqual(first_body['count'], 45)
        self.assertEqual(len(first_body['results']), 20)

        third_page = self.client.get(
            f'{LIST_URL}{conversation.id}/messages/',
            {'page': 3, 'page_size': 20},
        )
        self.assertEqual(len(third_page.json()['results']), 5)

    def test_inactive_conversation_get_detail_rejected(self):
        conversation = Conversation.objects.create(
            user=self.user,
            business_model=self.business_model,
            is_active=False,
        )
        self.client.force_authenticate(user=self.user)
        detail = self.client.get(f'{LIST_URL}{conversation.id}/')
        self.assertEqual(detail.status_code, 400)
        self.assertEqual(detail.json()['detail'], 'Conversation is inactive.')

        messages = self.client.get(f'{LIST_URL}{conversation.id}/messages/')
        self.assertEqual(messages.status_code, 400)

    def test_deterministic_message_ordering_with_created_at_tie(self):
        conversation = Conversation.objects.create(
            user=self.user,
            business_model=self.business_model,
        )
        lower_id = uuid.UUID('00000000-0000-4000-8000-000000000001')
        higher_id = uuid.UUID('00000000-0000-4000-8000-000000000002')
        first = Message.objects.create(
            id=lower_id,
            conversation=conversation,
            role=MessageRole.USER,
            content='Lower UUID sorts first when timestamps tie',
        )
        second = Message.objects.create(
            id=higher_id,
            conversation=conversation,
            role=MessageRole.ASSISTANT,
            content='Higher UUID',
        )
        tied_time = first.created_at
        Message.objects.filter(pk__in=[first.pk, second.pk]).update(created_at=tied_time)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'{LIST_URL}{conversation.id}/messages/')
        results = response.json()['results']
        self.assertEqual(results[0]['id'], str(first.id))
        self.assertEqual(results[1]['id'], str(second.id))

    def test_message_model_ordering_uses_id_tiebreaker(self):
        self.assertEqual(Message._meta.ordering, ['created_at', 'id'])

    def test_conversation_history_throttling(self):
        from django.core.cache import cache

        rest_framework = deepcopy(settings.REST_FRAMEWORK)
        rest_framework['DEFAULT_THROTTLE_RATES'] = {
            'chatbot_message': '2/minute',
            'conversation_history': '2/minute',
        }
        conversation = Conversation.objects.create(
            user=self.user,
            business_model=self.business_model,
        )
        self.client.force_authenticate(user=self.user)
        with override_settings(REST_FRAMEWORK=rest_framework):
            cache.clear()
            for _ in range(2):
                response = self.client.get(f'{LIST_URL}{conversation.id}/messages/')
                self.assertEqual(response.status_code, 200)
            throttled = self.client.get(f'{LIST_URL}{conversation.id}/messages/')
            self.assertEqual(throttled.status_code, 429)
