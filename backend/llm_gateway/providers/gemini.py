import os
from typing import Any

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from google.genai._interactions import (
    APITimeoutError as InteractionsAPITimeoutError,
    APIStatusError as InteractionsAPIStatusError,
)

from llm_gateway.gateway import LLMGatewayError
from llm_gateway.interfaces import LLMProvider, LLMRequest, LLMResponse

DEFAULT_GEMINI_MODEL = 'gemini-3.5-flash-lite'
DEFAULT_THINKING_LEVEL = 'low'
DEFAULT_TIMEOUT_MS = 60_000


class GeminiLLMProvider(LLMProvider):
    """Google Gemini provider using the official google-genai Interactions API."""

    provider_name = 'gemini'

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client: genai.Client | None = None,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> None:
        resolved_key = api_key if api_key is not None else os.environ.get('GEMINI_API_KEY', '')
        if model is not None:
            resolved_model = model
        else:
            env_model = os.environ.get('GEMINI_MODEL', DEFAULT_GEMINI_MODEL)
            resolved_model = env_model if env_model.strip() else DEFAULT_GEMINI_MODEL

        if not resolved_key.strip():
            raise LLMGatewayError('GEMINI_API_KEY is not configured')

        self._api_key = resolved_key
        self._model = resolved_model.strip()
        self._timeout_ms = timeout_ms
        self._client = client

    @property
    def model_name(self) -> str:
        return self._model

    def _get_client(self) -> genai.Client:
        if self._client is None:
            http_options = genai_types.HttpOptions(timeout=self._timeout_ms)
            self._client = genai.Client(api_key=self._api_key, http_options=http_options)
        return self._client

    def generate(self, request: LLMRequest) -> LLMResponse:
        create_kwargs: dict[str, Any] = {
            'model': self._model,
            'input': request.prompt,
            'timeout': self._timeout_ms / 1000.0,
            'generation_config': {'thinking_level': DEFAULT_THINKING_LEVEL},
        }
        if request.system_prompt and request.system_prompt.strip():
            create_kwargs['system_instruction'] = request.system_prompt.strip()

        try:
            interaction = self._get_client().interactions.create(**create_kwargs)
        except InteractionsAPITimeoutError as exc:
            raise LLMGatewayError('Gemini request timed out') from exc
        except InteractionsAPIStatusError as exc:
            raise self._map_status_error(exc) from exc
        except genai_errors.APIError as exc:
            raise self._map_genai_api_error(exc) from exc
        except httpx.TimeoutException as exc:
            raise LLMGatewayError('Gemini request timed out') from exc
        except httpx.HTTPError as exc:
            raise LLMGatewayError('Gemini network request failed') from exc

        content = self._extract_interaction_text(interaction)
        if not content:
            raise LLMGatewayError('Gemini returned an empty response')

        metadata: dict[str, Any] = {
            'provider': self.provider_name,
            'model': self._model,
        }
        if request.metadata:
            metadata['request_metadata'] = request.metadata

        return LLMResponse(content=content, metadata=metadata)

    @staticmethod
    def _extract_interaction_text(interaction: Any) -> str:
        status = getattr(interaction, 'status', None)
        if status == 'failed':
            return ''

        output_text = getattr(interaction, 'output_text', None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        step_parts: list[str] = []
        for step in getattr(interaction, 'steps', None) or []:
            if getattr(step, 'type', None) != 'model_output':
                continue
            for block in getattr(step, 'content', None) or []:
                if getattr(block, 'type', None) != 'text':
                    continue
                text = getattr(block, 'text', None)
                if text and str(text).strip():
                    step_parts.append(str(text).strip())
        if step_parts:
            return '\n'.join(step_parts).strip()

        legacy_parts: list[str] = []
        for block in getattr(interaction, 'outputs', None) or []:
            text = getattr(block, 'text', None)
            if text and str(text).strip():
                legacy_parts.append(str(text).strip())
        return '\n'.join(legacy_parts).strip()

    @staticmethod
    def _map_http_status(code: int | None) -> LLMGatewayError | None:
        if code in (401, 403):
            return LLMGatewayError('Gemini authentication failed')
        if code == 404:
            return LLMGatewayError('Gemini model unavailable')
        if code == 429:
            return LLMGatewayError('Gemini quota or rate limit exceeded')
        if code == 503:
            return LLMGatewayError('Gemini model temporarily unavailable')
        if code == 504:
            return LLMGatewayError('Gemini generation deadline exceeded')
        if code is not None and code >= 500:
            return LLMGatewayError('Gemini service unavailable')
        return None

    @staticmethod
    def _map_status_error(exc: InteractionsAPIStatusError) -> LLMGatewayError:
        mapped = GeminiLLMProvider._map_http_status(getattr(exc, 'status_code', None))
        if mapped is not None:
            return mapped
        return LLMGatewayError('Gemini API request failed')

    @staticmethod
    def _map_genai_api_error(exc: genai_errors.APIError) -> LLMGatewayError:
        mapped = GeminiLLMProvider._map_http_status(getattr(exc, 'code', None))
        if mapped is not None:
            return mapped
        return LLMGatewayError('Gemini API request failed')
