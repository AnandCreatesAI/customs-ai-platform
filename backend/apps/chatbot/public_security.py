"""Server-side checks for anonymous public chat (input refusal and output screening)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

_INJECTION_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r'ignore\s+(all\s+)?(previous|prior|above)\s+instructions', re.I),
    re.compile(r'disregard\s+(your\s+)?(system|safety)\s+(prompt|instructions)', re.I),
    re.compile(r'reveal\s+(the\s+)?(system|hidden)\s+prompt', re.I),
    re.compile(r'you\s+are\s+now\s+(in\s+)?developer\s+mode', re.I),
    re.compile(r'jailbreak', re.I),
    re.compile(r'bypass\s+(auth|authentication|security|restrictions)', re.I),
)

_SENSITIVE_REQUEST_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r'\b(other\s+users?|someone\s+else)\s+(records?|data|declarations?)\b', re.I),
    re.compile(r'\b(private|confidential|internal)\s+(documents?|records?|data)\b', re.I),
    re.compile(r'\b(api\s+key|password|secret\s+key|credentials?)\b', re.I),
    re.compile(r'\b(shipment|importer|exporter)\s+(details?|information)\s+for\b', re.I),
    re.compile(r'\b(ssn|social\s+security|aadhaar|passport\s+number)\b', re.I),
    re.compile(r'\b(illegal(ly)?\s+(import|export|evade|avoid))\b', re.I),
    re.compile(r'\bhow\s+to\s+(smuggle|evade\s+customs|avoid\s+duty)\b', re.I),
)

_OUTPUT_LEAK_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r'\bsessionid\s*=', re.I),
    re.compile(r'\b(api[_-]?key|secret[_-]?key)\s*[:=]', re.I),
    re.compile(r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----', re.I),
)


@dataclass(frozen=True)
class PublicChatRefusal:
    code: str
    message: str


_REFUSAL_SENSITIVE = PublicChatRefusal(
    code='sensitive_request',
    message=(
        'I cannot help with private, confidential, or unauthorized information. '
        'For account-specific or restricted data, please sign in with authorized access.'
    ),
)

_REFUSAL_INJECTION = PublicChatRefusal(
    code='prompt_injection',
    message='Your message could not be processed. Please ask a general customs or trade question.',
)


def evaluate_public_chat_input(message: str) -> PublicChatRefusal | None:
    normalized = message.strip()
    if not normalized:
        return PublicChatRefusal(
            code='empty_message',
            message='Message cannot be empty.',
        )

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(normalized):
            return _REFUSAL_INJECTION

    for pattern in _SENSITIVE_REQUEST_PATTERNS:
        if pattern.search(normalized):
            return _REFUSAL_SENSITIVE

    return None


def screen_public_chat_output(content: str) -> PublicChatRefusal | None:
    for pattern in _OUTPUT_LEAK_PATTERNS:
        if pattern.search(content):
            return PublicChatRefusal(
                code='output_blocked',
                message=(
                    'The assistant response could not be shown. '
                    'Please ask a general customs or trade question.'
                ),
            )
    return None
