"""
Shared validation for non-file training inputs (text and JSON).

No REST APIs in Phase 0; Employee Space and future upload endpoints will reuse these rules.
"""

from __future__ import annotations

import json

from django.core.exceptions import ValidationError

from apps.documents.training_file_policy import TRAINING_JSON_MAX_CHARS, TRAINING_TEXT_MAX_CHARS


def validate_training_text_title(title: str) -> str:
    cleaned = (title or '').strip()
    if not cleaned:
        raise ValidationError('Title is required.')
    return cleaned


def validate_training_text_content(content: str) -> str:
    if content is None:
        raise ValidationError('Text content is required.')
    if not str(content).strip():
        raise ValidationError('Text content cannot be empty.')
    if len(content) > TRAINING_TEXT_MAX_CHARS:
        raise ValidationError('Text content exceeds the configured character limit.')
    return content


def validate_training_json_title(title: str) -> str:
    return validate_training_text_title(title)


def validate_training_json_content(content: str) -> str:
    if content is None:
        raise ValidationError('JSON content is required.')
    raw = str(content)
    if not raw.strip():
        raise ValidationError('JSON content cannot be empty.')
    if len(raw) > TRAINING_JSON_MAX_CHARS:
        raise ValidationError('JSON content exceeds the configured character limit.')
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError('JSON content is not valid JSON.') from exc
    if not isinstance(parsed, (dict, list)):
        raise ValidationError('JSON must be a top-level object or array.')
    return raw
