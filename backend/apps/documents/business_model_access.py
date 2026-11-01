from django.core.exceptions import ValidationError

from apps.model_management.models import BusinessModel


def get_active_business_model(key: str) -> BusinessModel:
    normalized = (key or '').strip()
    if not normalized:
        raise ValidationError({'business_model': 'Business model is required.'})

    try:
        business_model = BusinessModel.objects.get(key=normalized)
    except BusinessModel.DoesNotExist as exc:
        raise ValidationError({'business_model': 'Unknown business model.'}) from exc

    if not business_model.is_active:
        raise ValidationError({'business_model': 'Business model is not active.'})

    return business_model
