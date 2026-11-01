import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from apps.documents.models import Document, DocumentStatus
from apps.knowledge.models import (
    KnowledgeIndexingStatus,
    KnowledgeSource,
    KnowledgeSourceType,
    KnowledgeVisibility,
)
from apps.model_management.models import BusinessModel, BusinessModelKey

User = get_user_model()


class KnowledgeTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='knowledge-owner@example.com',
            password='secure-pass-123',
        )
        self.other_user = User.objects.create_user(
            email='knowledge-other@example.com',
            password='secure-pass-123',
        )
        self.business_model = BusinessModel.objects.create(
            key=BusinessModelKey.HS_CODE,
            name='HS Code Model',
        )
        self.document = Document.objects.create(
            user=self.other_user,
            business_model=self.business_model,
            original_filename='hs-reference.txt',
            file_path='uploads/hs-reference.txt',
            file_size=512,
            status=DocumentStatus.UPLOADED,
        )

    def _source(self, **overrides):
        data = {
            'business_model': self.business_model,
            'source_type': KnowledgeSourceType.MANUAL,
            'title': 'HS guidance notes',
            'visibility': KnowledgeVisibility.PRIVATE,
            'user': self.user,
        }
        data.update(overrides)
        return KnowledgeSource(**data)


class KnowledgeSourceModelTests(KnowledgeTestBase):
    def test_create_shared_knowledge_without_owner(self):
        source = self._source(
            visibility=KnowledgeVisibility.SHARED,
            user=None,
            title='Platform HS FAQ',
        )
        source.full_clean()
        source.save()
        self.assertIsNone(source.user_id)

    def test_create_shared_knowledge_with_associated_owner(self):
        source = self._source(
            visibility=KnowledgeVisibility.SHARED,
            user=self.user,
            title='Curated HS FAQ',
        )
        source.full_clean()
        source.save()
        self.assertEqual(source.user, self.user)

    def test_create_private_knowledge_with_owner(self):
        source = self._source(
            visibility=KnowledgeVisibility.PRIVATE,
            user=self.user,
        )
        source.full_clean()
        source.save()
        self.assertEqual(source.user, self.user)

    def test_reject_private_knowledge_without_owner(self):
        source = self._source(
            visibility=KnowledgeVisibility.PRIVATE,
            user=None,
        )
        with self.assertRaises(ValidationError):
            source.full_clean()

    def test_uuid_primary_key(self):
        source = self._source()
        source.save()
        self.assertIsInstance(source.id, uuid.UUID)

    def test_default_indexing_status_is_pending(self):
        source = self._source()
        source.save()
        self.assertEqual(source.indexing_status, KnowledgeIndexingStatus.PENDING)

    def test_valid_source_types(self):
        values = {choice.value for choice in KnowledgeSourceType}
        self.assertEqual(values, {'document', 'text', 'url', 'manual'})

    def test_valid_visibility_choices(self):
        values = {choice.value for choice in KnowledgeVisibility}
        self.assertEqual(values, {'shared', 'private'})

    def test_business_model_protect_on_delete(self):
        source = self._source()
        source.save()
        with self.assertRaises(ProtectedError):
            self.business_model.delete()

    def test_user_deletion_set_null_for_shared_source(self):
        source = self._source(
            visibility=KnowledgeVisibility.SHARED,
            user=self.user,
        )
        source.save()
        self.user.delete()
        source.refresh_from_db()
        self.assertIsNone(source.user_id)

    def test_document_deletion_set_null(self):
        source = self._source(
            source_type=KnowledgeSourceType.DOCUMENT,
            document=self.document,
            visibility=KnowledgeVisibility.SHARED,
            user=None,
        )
        source.save()
        document_id = self.document.id
        self.document.delete()
        source.refresh_from_db()
        self.assertIsNone(source.document_id)
        self.assertFalse(Document.objects.filter(id=document_id).exists())


class KnowledgeMetadataAndVectorTests(KnowledgeTestBase):
    def test_metadata_dictionary_validation(self):
        source = self._source(metadata={'language': 'en', 'tags': ['hs', 'import']})
        source.full_clean()
        source.save()
        source.refresh_from_db()
        self.assertEqual(source.metadata['language'], 'en')

    def test_secret_like_metadata_key_rejection(self):
        source = self._source(metadata={'api_key': 'must-not-store'})
        with self.assertRaises(ValidationError):
            source.full_clean()

    def test_optional_vector_store_reference(self):
        source = self._source(
            visibility=KnowledgeVisibility.SHARED,
            user=None,
            vector_store='external://vector-store/collection/point-123',
        )
        source.full_clean()
        source.save()
        self.assertEqual(source.vector_store, 'external://vector-store/collection/point-123')

    def test_no_embedding_field_exists(self):
        field_names = {field.name for field in KnowledgeSource._meta.get_fields()}
        self.assertFalse({'embedding', 'embeddings', 'vector'}.intersection(field_names))


class KnowledgeDataIsolationTests(KnowledgeTestBase):
    def test_private_knowledge_ownership_represented_correctly(self):
        private_source = self._source(
            visibility=KnowledgeVisibility.PRIVATE,
            user=self.user,
            title='Private notes',
        )
        private_source.save()
        self.assertEqual(private_source.user.email, 'knowledge-owner@example.com')
        self.assertEqual(self.user.knowledge_sources.count(), 1)

    def test_shared_knowledge_can_be_ownerless(self):
        shared_source = self._source(
            visibility=KnowledgeVisibility.SHARED,
            user=None,
            title='Shared corpus',
        )
        shared_source.save()
        self.assertIsNone(shared_source.user)

    def test_document_and_knowledge_ownership_remain_separate(self):
        source = self._source(
            source_type=KnowledgeSourceType.DOCUMENT,
            document=self.document,
            visibility=KnowledgeVisibility.PRIVATE,
            user=self.user,
        )
        source.save()
        self.assertEqual(source.user, self.user)
        self.assertEqual(self.document.user, self.other_user)
        self.assertNotEqual(source.user_id, self.document.user_id)

    def test_private_without_owner_rejected_at_database_level(self):
        source = KnowledgeSource(
            business_model=self.business_model,
            source_type=KnowledgeSourceType.TEXT,
            title='Invalid private source',
            visibility=KnowledgeVisibility.PRIVATE,
            user=None,
        )
        with self.assertRaises((ValidationError, IntegrityError)):
            with transaction.atomic():
                source.save()
