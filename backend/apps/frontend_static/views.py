from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseNotFound
from django.views.decorators.http import require_GET

_FRONTEND_HTML_ROUTES: dict[str, str] = {
    '/': 'index.html',
    '/login': 'login.html',
    '/dashboard': 'dashboard.html',
    '/dashboard/employee-space': 'dashboard/employee-space.html',
}


def _export_root() -> Path:
    root = getattr(settings, 'FRONTEND_EXPORT_ROOT', None)
    if root is None:
        raise Http404('Frontend export is not configured.')
    path = Path(root)
    if not path.is_dir():
        raise Http404('Frontend export directory is missing.')
    return path


def _resolve_html(relative: str) -> Path | None:
    root = _export_root()
    candidate = root / relative
    if candidate.is_file():
        return candidate
    return None


def _normalize_path(path: str) -> str:
    if not path or path == '/':
        return '/'
    return '/' + path.strip('/')


@require_GET
def serve_frontend_page(request, path: str = ''):
    if path.startswith('api/') or path.startswith('admin/'):
        return HttpResponseNotFound('Not found')

    normalized = _normalize_path(path)
    relative = _FRONTEND_HTML_ROUTES.get(normalized)
    if relative is None:
        return HttpResponseNotFound('Not found')

    file_path = _resolve_html(relative)
    if file_path is None:
        return HttpResponseNotFound('Not found')

    return FileResponse(file_path.open('rb'), content_type='text/html; charset=utf-8')


@require_GET
def serve_frontend_public_asset(request, asset_path: str):
    if '..' in asset_path.split('/'):
        return HttpResponseNotFound('Not found')

    root = _export_root()
    file_path = root / asset_path
    if not file_path.is_file():
        return HttpResponseNotFound('Not found')

    return FileResponse(file_path.open('rb'))
