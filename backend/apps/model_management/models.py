import re
import uuid

from django.core.exceptions import ValidationError
from django.db import models

ENV_VAR_NAME_PATTERN = re.compile(r'^[A-Z][A-Z0-9_]*$')

FORBIDDEN_CONFIG_KEYS = frozenset(
    {
        'api_key',
        'apikey',
        'password',
        'secret',
        'token',
        'access_token',
        'refresh_token',
        'private_key',
    }
)


class BusinessModelKey(models.TextChoices):
    USER = 'user', 'User'
    EBOOKS = 'ebooks', 'eBooks'
    EMPLOYEE = 'employee', 'Employee'
    HS_CODE = 'hs_code', 'HS Code'


class BusinessModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=32, choices=BusinessModelKey.choices, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['key']
        verbose_name = 'business model'
        verbose_name_plural = 'business models'

    def __str__(self) -> str:
        return f'{self.name} ({self.key})'


class LLMProviderProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider_key = models.SlugField(max_length=32, unique=True)
    display_name = models.CharField(max_length=128)
    model_name = models.CharField(max_length=128)
    api_key_env_var = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    configuration = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['provider_key']
        verbose_name = 'LLM provider profile'
        verbose_name_plural = 'LLM provider profiles'

    def __str__(self) -> str:
        return f'{self.display_name} ({self.provider_key})'

    def clean(self) -> None:
        super().clean()
        if self.api_key_env_var and not ENV_VAR_NAME_PATTERN.match(self.api_key_env_var):
            raise ValidationError(
                {
                    'api_key_env_var': (
                        'Must be a valid environment variable name (e.g. GEMINI_API_KEY).'
                    ),
                }
            )
        self._validate_configuration_is_non_secret(self.configuration)

    @classmethod
    def _validate_configuration_is_non_secret(cls, configuration) -> None:
        if configuration in (None, ''):
            return
        if not isinstance(configuration, dict):
            raise ValidationError({'configuration': 'Configuration must be a JSON object.'})

        def walk(prefix: str, value) -> None:
            if isinstance(value, dict):
                for key, nested in value.items():
                    if str(key).lower() in FORBIDDEN_CONFIG_KEYS:
                        raise ValidationError(
                            {
                                'configuration': (
                                    f'Secret-like key "{key}" is not allowed in configuration.'
                                ),
                            }
                        )
                    walk(f'{prefix}.{key}' if prefix else str(key), nested)
            elif isinstance(value, list):
                for item in value:
                    walk(prefix, item)

        walk('', configuration)
