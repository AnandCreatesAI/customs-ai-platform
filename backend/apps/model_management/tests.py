import uuid

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.model_management.models import BusinessModel, BusinessModelKey, LLMProviderProfile


class BusinessModelTests(TestCase):
    def test_create_all_four_supported_business_models(self):
        keys = [
            BusinessModelKey.USER,
            BusinessModelKey.EBOOKS,
            BusinessModelKey.EMPLOYEE,
            BusinessModelKey.HS_CODE,
        ]
        for key in keys:
            BusinessModel.objects.create(key=key, name=f'{key} model')
        self.assertEqual(BusinessModel.objects.count(), 4)

    def test_unique_model_keys(self):
        BusinessModel.objects.create(key=BusinessModelKey.USER, name='User Model')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                BusinessModel.objects.create(key=BusinessModelKey.USER, name='Duplicate')

    def test_default_active_status(self):
        model = BusinessModel.objects.create(key=BusinessModelKey.USER, name='User Model')
        self.assertTrue(model.is_active)

    def test_uuid_primary_key(self):
        model = BusinessModel.objects.create(key=BusinessModelKey.USER, name='User Model')
        self.assertIsInstance(model.id, uuid.UUID)

    def test_string_representation(self):
        model = BusinessModel.objects.create(key=BusinessModelKey.HS_CODE, name='HS Code Model')
        self.assertEqual(str(model), 'HS Code Model (hs_code)')


class LLMProviderProfileTests(TestCase):
    def _valid_profile(self, **overrides):
        data = {
            'provider_key': 'gemini',
            'display_name': 'Google Gemini',
            'model_name': 'gemini-model-placeholder',
            'api_key_env_var': 'GEMINI_API_KEY',
            'configuration': {'timeout_seconds': 30},
        }
        data.update(overrides)
        return LLMProviderProfile(**data)

    def test_create_gemini_provider_profile_metadata_only(self):
        profile = self._valid_profile()
        profile.full_clean()
        profile.save()
        self.assertEqual(profile.provider_key, 'gemini')
        self.assertEqual(profile.api_key_env_var, 'GEMINI_API_KEY')

    def test_unique_provider_keys(self):
        profile = self._valid_profile()
        profile.save()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._valid_profile().save()

    def test_validate_environment_variable_name(self):
        profile = self._valid_profile(api_key_env_var='invalid-env-name')
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_default_active_status(self):
        profile = self._valid_profile()
        profile.save()
        self.assertTrue(profile.is_active)

    def test_configuration_json_field_behavior(self):
        profile = self._valid_profile(configuration={'max_output_tokens': 1024, 'nested': {'retries': 2}})
        profile.full_clean()
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.configuration['max_output_tokens'], 1024)

    def test_configuration_rejects_secret_like_keys(self):
        profile = self._valid_profile(configuration={'api_key': 'must-not-store'})
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_uuid_primary_key(self):
        profile = self._valid_profile()
        profile.save()
        self.assertIsInstance(profile.id, uuid.UUID)

    def test_string_representation(self):
        profile = self._valid_profile()
        profile.save()
        self.assertEqual(str(profile), 'Google Gemini (gemini)')

    def test_no_secret_value_fields_on_model(self):
        field_names = {field.name for field in LLMProviderProfile._meta.get_fields()}
        forbidden = {'api_key', 'password', 'secret', 'token', 'access_token'}
        self.assertTrue(forbidden.isdisjoint(field_names))
        self.assertIn('api_key_env_var', field_names)


class SeedBusinessModelsCommandTests(TestCase):
    def test_creates_all_four_business_models(self):
        call_command('seed_business_models')
        self.assertEqual(BusinessModel.objects.count(), 4)
        keys = set(BusinessModel.objects.values_list('key', flat=True))
        self.assertEqual(
            keys,
            {
                BusinessModelKey.USER,
                BusinessModelKey.EBOOKS,
                BusinessModelKey.EMPLOYEE,
                BusinessModelKey.HS_CODE,
            },
        )

    def test_idempotent_no_duplicates(self):
        call_command('seed_business_models')
        call_command('seed_business_models')
        self.assertEqual(BusinessModel.objects.count(), 4)

    def test_does_not_overwrite_customized_descriptions(self):
        call_command('seed_business_models')
        model = BusinessModel.objects.get(key=BusinessModelKey.USER)
        model.description = 'Custom description for operators'
        model.save(update_fields=['description'])

        call_command('seed_business_models')
        model.refresh_from_db()
        self.assertEqual(model.description, 'Custom description for operators')
