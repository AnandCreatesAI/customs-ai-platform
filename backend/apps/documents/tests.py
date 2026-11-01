import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase

from apps.conversations.models import Conversation
from apps.documents.models import Document, DocumentStatus
from apps.model_management.models import BusinessModel, BusinessModelKey

User = get_user_model()


class DocumentsTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='doc-owner@example.com',
            password='secure-pass-123',
        )
        self.other_user = User.objects.create_user(
            email='doc-other@example.com',
            password='secure-pass-123',
        )
        self.business_model = BusinessModel.objects.create(
            key=BusinessModelKey.EBOOKS,
            name='eBooks Model',
        )

    def _valid_document(self, **overrides):
        data = {
            'user': self.user,
            'business_model': self.business_model,
            'original_filename': 'customs-guide.PDF',
            'file_path': 'uploads/2026/11/customs-guide.pdf',
            'file_size': 2048,
            'metadata': {'source': 'manual-upload'},
        }
        data.update(overrides)
        return Document(**data)


class DocumentCreationTests(DocumentsTestBase):
    def test_create_document_for_authenticated_user(self):
        document = self._valid_document()
        document.full_clean()
        document.save()
        self.assertEqual(document.user, self.user)

    def test_associates_existing_business_model(self):
        document = self._valid_document()
        document.save()
        self.assertEqual(document.business_model.key, BusinessModelKey.EBOOKS)

    def test_uuid_primary_key(self):
        document = self._valid_document()
        document.save()
        self.assertIsInstance(document.id, uuid.UUID)

    def test_default_status_is_uploaded(self):
        document = self._valid_document()
        document.save()
        self.assertEqual(document.status, DocumentStatus.UPLOADED)

    def test_required_filename_validation(self):
        document = self._valid_document(original_filename='   ')
        with self.assertRaises(ValidationError):
            document.full_clean()

    def test_file_size_validation_requires_value(self):
        document = self._valid_document()
        document.file_size = None
        with self.assertRaises(ValidationError):
            document.full_clean()

    def test_file_type_normalization(self):
        document = self._valid_document(original_filename='Report.PDF', file_type='.PDF')
        document.full_clean()
        self.assertEqual(document.file_type, 'pdf')

    def test_metadata_json_validation(self):
        document = self._valid_document(metadata={'pages': 12})
        document.full_clean()
        document.save()
        document.refresh_from_db()
        self.assertEqual(document.metadata['pages'], 12)

    def test_metadata_rejects_secret_like_keys(self):
        document = self._valid_document(metadata={'token': 'secret'})
        with self.assertRaises(ValidationError):
            document.full_clean()


class DocumentRelationshipTests(DocumentsTestBase):
    def test_user_deletion_cascades_documents(self):
        document = self._valid_document()
        document.save()
        document_id = document.id
        self.user.delete()
        self.assertFalse(Document.objects.filter(id=document_id).exists())

    def test_business_model_deletion_protects_documents(self):
        document = self._valid_document()
        document.save()
        with self.assertRaises(ProtectedError):
            self.business_model.delete()

    def test_different_users_own_separate_documents(self):
        doc_a = self._valid_document(user=self.user, original_filename='a.txt')
        doc_a.save()
        Document.objects.create(
            user=self.other_user,
            business_model=self.business_model,
            original_filename='b.txt',
            file_path='uploads/b.txt',
            file_size=100,
        )
        self.assertEqual(self.user.documents.count(), 1)
        self.assertEqual(self.other_user.documents.count(), 1)
        self.assertNotEqual(doc_a.user_id, self.other_user.id)

    def test_document_ownership_independent_of_conversations(self):
        document = self._valid_document()
        document.save()
        conversation = Conversation.objects.create(
            user=self.user,
            business_model=self.business_model,
            title='Separate thread',
        )
        self.assertIsNone(getattr(document, 'conversation', None))
        self.assertNotEqual(document._meta.get_field('user').remote_field.model, Conversation)


class DocumentAdditionalValidationTests(DocumentsTestBase):
    def test_status_choices(self):
        choices = {choice.value for choice in DocumentStatus}
        self.assertEqual(
            choices,
            {'uploaded', 'processing', 'processed', 'failed', 'archived'},
        )

    def test_checksum_indexing(self):
        field = Document._meta.get_field('checksum')
        self.assertTrue(field.db_index)

    def test_migration_is_configured(self):
        from django.db.migrations.loader import MigrationLoader

        loader = MigrationLoader(None, ignore_no_migrations=False)
        self.assertIn(('documents', '0001_initial'), loader.graph.nodes)
