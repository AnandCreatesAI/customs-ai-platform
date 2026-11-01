from __future__ import annotations

import re

from apps.rag.exceptions import RagCitationError

# Numeric inline citations only, e.g. [1], [12]. Non-matching bracket text is ignored.
_CITATION_PATTERN = re.compile(r'\[(\d+)\]')


def extract_citation_refs(answer: str) -> set[int]:
    if not answer:
        return set()
    refs: set[int] = set()
    for match in _CITATION_PATTERN.finditer(answer):
        try:
            refs.add(int(match.group(1)))
        except ValueError:
            continue
    return refs


def validate_answer_citations(*, answer: str, valid_refs: set[int]) -> None:
    """
    Validate inline [n] citations against server-assigned source numbers.

    When valid_refs is empty (no-sources path), validation is a no-op.

    Rules when valid_refs is non-empty:
    - At least one numeric citation must appear in the answer.
    - Every extracted citation must be a member of valid_refs (no out-of-range refs).
    - Mixed valid and invalid citations fail (e.g. [1] and [99] when only 1 exists).
    - Duplicate citations (e.g. [1] twice) are allowed.
    - Malformed markers such as [abc] are ignored and do not count as citations.
    - Source UUIDs in prose are not validated here; sources in API/metadata are server-only.
    """
    if not valid_refs:
        return

    cited = extract_citation_refs(answer)
    if not cited:
        raise RagCitationError()

    invalid = cited - valid_refs
    if invalid:
        raise RagCitationError(
            'Assistant response citations must only use retrieved source numbers '
            f'{sorted(valid_refs)}; invalid references: {sorted(invalid)}.',
        )
