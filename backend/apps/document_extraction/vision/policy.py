from apps.document_extraction.conf import vision_enabled


def vision_allowed() -> bool:
    return vision_enabled()
