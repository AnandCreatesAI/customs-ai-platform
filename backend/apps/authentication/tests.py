from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

User = get_user_model()


class UserModelTests(TestCase):
    def test_create_user_with_email_and_password(self):
        user = User.objects.create_user(
            email='person@example.com',
            password='secure-pass-123',
        )
        self.assertEqual(user.email, 'person@example.com')
        self.assertTrue(user.check_password('secure-pass-123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_email_normalization(self):
        user = User.objects.create_user(
            email='Person@Example.COM',
            password='secure-pass-123',
        )
        self.assertEqual(user.email, 'Person@example.com')

    def test_password_is_hashed_not_plaintext(self):
        raw_password = 'secure-pass-123'
        user = User.objects.create_user(email='hash@example.com', password=raw_password)
        self.assertNotEqual(user.password, raw_password)
        self.assertTrue(user.password.startswith('pbkdf2_sha256$'))
        self.assertTrue(user.check_password(raw_password))
        self.assertFalse(user.check_password('wrong-password'))

    def test_duplicate_email_rejected(self):
        User.objects.create_user(email='dup@example.com', password='secure-pass-123')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(email='dup@example.com', password='other-pass-456')

    def test_default_role_is_user(self):
        user = User.objects.create_user(email='role@example.com', password='secure-pass-123')
        self.assertEqual(user.role, 'user')

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='secure-pass-123',
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_superuser_requires_staff_and_superuser_flags(self):
        with self.assertRaisesMessage(ValueError, 'Superuser must have is_staff=True.'):
            User.objects.create_superuser(
                email='bad1@example.com',
                password='secure-pass-123',
                is_staff=False,
            )
        with self.assertRaisesMessage(ValueError, 'Superuser must have is_superuser=True.'):
            User.objects.create_superuser(
                email='bad2@example.com',
                password='secure-pass-123',
                is_superuser=False,
            )

    def test_username_not_required_for_user_creation(self):
        user = User.objects.create_user(email='no-username@example.com', password='secure-pass-123')
        self.assertFalse(hasattr(user, 'username') and user.username is not None)

    def test_auth_user_model_setting(self):
        self.assertEqual(settings.AUTH_USER_MODEL, 'authentication.User')
