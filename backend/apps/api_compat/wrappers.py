"""Thin wrappers matching legacy Next.js BFF validation before delegating to DRF views."""

from django.http import JsonResponse

from apps.api_compat.validation import is_valid_uuid


class InvalidUuidMixin:
    invalid_detail: str = 'Invalid id.'

    def dispatch(self, request, *args, **kwargs):
        for key in ('conversation_id', 'message_id', 'document_id', 'job_id'):
            if key in kwargs and not is_valid_uuid(str(kwargs[key])):
                detail = self.invalid_detail
                if key == 'conversation_id':
                    detail = 'Invalid conversation id.'
                elif key == 'message_id':
                    detail = 'Invalid message id.'
                elif key == 'document_id':
                    detail = 'Invalid document id.'
                elif key == 'job_id':
                    detail = 'Invalid training job id.'
                return JsonResponse({'detail': detail}, status=400)
        return super().dispatch(request, *args, **kwargs)


def wrap_view(view_class, mixin=InvalidUuidMixin, **mixin_kwargs):
    name = f'Compat{view_class.__name__}'
    return type(name, (mixin, view_class), mixin_kwargs)
