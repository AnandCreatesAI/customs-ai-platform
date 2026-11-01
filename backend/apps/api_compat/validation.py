import re
from uuid import UUID

_UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.IGNORECASE,
)


def is_valid_uuid(value: str) -> bool:
    if not _UUID_PATTERN.match(value):
        return False
    try:
        UUID(value)
    except ValueError:
        return False
    return True
