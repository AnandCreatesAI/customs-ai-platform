from __future__ import annotations

import re

DEFAULT_CONVERSATION_TITLE = 'New conversation'
_PLACEHOLDER_TITLES = frozenset(
    {
        '',
        DEFAULT_CONVERSATION_TITLE,
        'Untitled conversation',
    }
)

# Titles that are too vague to represent a conversation topic (whole-title match, lowercased).
_GENERIC_TITLES = frozenset(
    {
        'chat',
        'custom',
        'help',
        'info',
        'new chat',
        'question',
        'support',
        'thread',
        'query',
    }
)

_TITLE_CASE_SMALL_WORDS = frozenset(
    {
        'a',
        'an',
        'and',
        'as',
        'at',
        'but',
        'by',
        'for',
        'in',
        'nor',
        'of',
        'on',
        'or',
        'per',
        'the',
        'to',
        'vs',
        'via',
    }
)

# Conversational openers (language patterns only — not topic-specific).
_OPENER_REGEXES = (
    re.compile(
        r'^(?:please\s+)?(?:can you|could you)\s+(?:please\s+)?'
        r'(?:explain|describe|tell me about)\s+',
        re.IGNORECASE,
    ),
    re.compile(r'^(?:please\s+)?(?:explain|describe)\s+', re.IGNORECASE),
    re.compile(r'^tell me about\s+', re.IGNORECASE),
    re.compile(r'^help me understand\s+', re.IGNORECASE),
    re.compile(r'^i want to know about\s+', re.IGNORECASE),
    re.compile(r'^i need to know about\s+', re.IGNORECASE),
    re.compile(r'^please tell me\s+', re.IGNORECASE),
    re.compile(r'^please help me with\s+', re.IGNORECASE),
)

# Intent patterns run on normalized lowercase text; groups supply subject spans.
_INTENT_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r'^what is the importance of (?P<subject>.+)$'),
        'Importance of {subject}',
    ),
    (
        re.compile(r'^what is the role of (?P<subject>.+)$'),
        'Role of {subject}',
    ),
    (
        re.compile(r'^what is the purpose of (?P<subject>.+)$'),
        'Purpose of {subject}',
    ),
    (
        re.compile(r'^what is the meaning of (?P<subject>.+)$'),
        'Meaning of {subject}',
    ),
    (
        re.compile(r'^what is an? (?P<subject>.+)$'),
        '{subject} Explained',
    ),
    (
        re.compile(r'^what is the (?P<subject>.+)$'),
        'Understanding {subject}',
    ),
    (
        re.compile(r'^what is (?P<subject>.+)$'),
        'Understanding {subject}',
    ),
    (
        re.compile(r'^what are (?:the )?(?P<subject>.+)$'),
        'Understanding {subject}',
    ),
    (
        re.compile(
            r'^how does (?P<core>.+?) work in (?P<context>.+)$',
        ),
        '{context} {core}',
    ),
    (
        re.compile(r'^how does (?P<core>.+?) work$'),
        '{core}',
    ),
    (
        re.compile(r'^how (?:do|can|should) (?P<subject>.+)$'),
        '{subject}',
    ),
    (
        re.compile(r'^why (?:is|are|do|does) (?P<subject>.+)$'),
        '{subject}',
    ),
)


def is_placeholder_conversation_title(title: str) -> bool:
    return title.strip() in _PLACEHOLDER_TITLES


def truncate_plain_title(message: str, *, max_length: int = 255) -> str:
    text = _collapse_whitespace(message)
    if not text:
        return ''
    text = text.rstrip('.?!').strip()
    if not text:
        return ''
    if len(text) > max_length:
        truncated = text[: max_length - 1].rstrip()
        return f'{truncated}…'

    working = _strip_conversational_openers(text)
    if working.lower() != text.lower():
        restored = _restore_phrase_preserve_casing(working, message)
        if restored:
            return _format_title_words(restored.split())

    excerpt = _restore_phrase_preserve_casing(working, message)
    if not excerpt:
        return ''
    return excerpt[0].upper() + excerpt[1:] if len(excerpt) > 1 else excerpt.upper()


def generate_conversation_title(message: str, *, max_length: int = 255) -> str:
    text = _collapse_whitespace(message)
    if not text:
        return ''

    text = text.rstrip('.?!').strip()
    working = _strip_conversational_openers(text)
    title = _title_from_intent(working, text)
    if not title:
        title = _title_from_declarative_subject(working, text)

    if not title or _is_weak_title(title):
        title = _title_from_declarative_subject(text, text)

    if not title:
        return ''

    title = _trim_to_word_window(title, max_words=7)
    title = _cap_length(title, max_length=max_length)
    return title


def title_from_user_message(message: str, *, max_length: int = 255) -> str:
    """
    Derive a stable sidebar title from the first user message without LLM calls.
    Never returns a generic placeholder when the message has visible content.
    """
    generated = generate_conversation_title(message, max_length=max_length)
    if generated and not is_placeholder_conversation_title(generated) and not _is_weak_title(
        generated,
    ):
        return generated
    fallback = truncate_plain_title(message, max_length=max_length)
    if fallback and not _is_weak_title(fallback):
        return fallback
    return generated or fallback


def _collapse_whitespace(message: str) -> str:
    return re.sub(r'\s+', ' ', message.strip())


def _strip_conversational_openers(text: str) -> str:
    remainder = text
    changed = True
    while changed:
        changed = False
        for pattern in _OPENER_REGEXES:
            match = pattern.match(remainder)
            if match:
                remainder = remainder[match.end() :].strip()
                changed = True
                break
    return remainder


def _title_from_intent(working: str, source: str) -> str:
    lower = working.lower().strip()
    if not lower:
        return ''

    for pattern, template in _INTENT_RULES:
        match = pattern.match(lower)
        if not match:
            continue
        groups = {
            key: _restore_words_from_source(value.strip(), source)
            for key, value in match.groupdict().items()
        }
        subject = groups.get('subject') or groups.get('core') or ''
        if 'subject' in groups and groups['subject']:
            subject = _first_meaningful_clause(groups['subject'])
        elif 'core' in groups and 'context' in groups:
            core = _first_meaningful_clause(groups['core'])
            context = _first_meaningful_clause(groups['context'])
            phrase = f'{context} {core}'.strip()
            return _finalize_phrase(phrase, source, suffix_explained=False)
        else:
            subject = _first_meaningful_clause(subject or working)

        if not subject:
            continue

        phrase = template.format(**{**groups, 'subject': subject})
        suffix_explained = phrase.lower().endswith(' explained')
        return _finalize_phrase(phrase, source, suffix_explained=suffix_explained)

    return ''


def _title_from_declarative_subject(working: str, source: str) -> str:
    subject = _first_meaningful_clause(working)
    if not subject:
        return ''
    lower = subject.lower()
    if lower.startswith('explain '):
        subject = subject[8:].strip()
    subject = _first_meaningful_clause(subject)
    if not subject:
        return ''

    restored = _restore_words_from_source(subject, source)
    word_count = len(restored.split())
    source_lower = source.lower()
    if _should_add_explained_suffix(source_lower, word_count):
        return _finalize_phrase(f'{restored} Explained', source, suffix_explained=True)
    return _finalize_phrase(restored, source, suffix_explained=False)


def _should_add_explained_suffix(source_lower: str, word_count: int) -> bool:
    if 'tell me about' in source_lower or 'help me understand' in source_lower:
        return word_count <= 4
    if 'explain' in source_lower or 'describe' in source_lower:
        return word_count <= 2
    return False


def _first_meaningful_clause(text: str) -> str:
    clause = text
    for separator in ('\n', '. ', '?', ';'):
        if separator in clause:
            clause = clause.split(separator, 1)[0]
    if len(clause) > 120 and ',' in clause:
        clause = clause.split(',', 1)[0]
    return clause.strip()


def _restore_phrase_preserve_casing(phrase: str, source: str) -> str:
    words = phrase.split()
    if not words:
        return ''
    return ' '.join(_restore_single_word(word, source) for word in words)


def _restore_words_from_source(phrase: str, source: str) -> str:
    restored = _restore_phrase_preserve_casing(phrase, source)
    if not restored:
        return ''
    return _format_title_words(restored.split())


def _restore_single_word(word: str, source: str) -> str:
    pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
    match = pattern.search(source)
    if not match:
        return word.capitalize()
    return match.group(0)


def _format_title_words(words: list[str]) -> str:
    formatted: list[str] = []
    for index, word in enumerate(words):
        if not word:
            continue
        if word.isupper() and len(word) >= 2:
            formatted.append(word)
            continue
        if index == 0:
            formatted.append(_capitalize_word(word))
            continue
        if word.lower() in _TITLE_CASE_SMALL_WORDS:
            formatted.append(word.lower())
        else:
            formatted.append(_capitalize_word(word))
    return ' '.join(formatted)


def _capitalize_word(word: str) -> str:
    if not word:
        return word
    if word.isupper() and len(word) >= 2:
        return word
    if len(word) <= 3 and word.isalpha() and word.isupper():
        return word
    return word[0].upper() + word[1:].lower()


def _finalize_phrase(phrase: str, source: str, *, suffix_explained: bool) -> str:
    cleaned = _collapse_whitespace(phrase)
    if suffix_explained and not cleaned.lower().endswith('explained'):
        cleaned = f'{cleaned} Explained'
    words = cleaned.split()
    formatted = _format_title_words(words)
    if _is_weak_title(formatted):
        return ''
    return formatted


def _trim_to_word_window(title: str, *, max_words: int) -> str:
    words = title.split()
    if len(words) <= max_words:
        return title
    trimmed = words[:max_words]
    while trimmed and trimmed[-1].lower() in _TITLE_CASE_SMALL_WORDS:
        trimmed.pop()
    return ' '.join(trimmed) if trimmed else ' '.join(words[:max_words])


def _cap_length(title: str, *, max_length: int) -> str:
    if len(title) <= max_length:
        return title
    truncated = title[: max_length - 1].rstrip()
    if ' ' in truncated:
        truncated = truncated.rsplit(' ', 1)[0]
    return f'{truncated}…'


def _is_weak_title(title: str) -> bool:
    cleaned = title.strip()
    if not cleaned:
        return True
    lower = cleaned.lower()
    if lower in _GENERIC_TITLES or is_placeholder_conversation_title(cleaned):
        return True
    words = cleaned.split()
    if len(words) == 1 and len(words[0]) <= 4 and words[0].isalpha():
        return True
    return False


def is_legacy_deterministic_title(stored_title: str, first_user_message: str) -> bool:
    """
    True when the stored title exactly matches the old deterministic generator
    (used to safely refresh legacy rows without touching manual or LLM titles).
    """
    cleaned = stored_title.strip()
    if not cleaned.lower().startswith('understanding '):
        return False
    auto_title = title_from_user_message(first_user_message)
    return cleaned == auto_title
