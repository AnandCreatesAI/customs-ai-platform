import logging

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class FrontendStaticConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.frontend_static'
    verbose_name = 'Next.js static frontend'

    def ready(self) -> None:
        export_root = getattr(settings, 'FRONTEND_EXPORT_ROOT', None)
        if export_root is None:
            return
        marker = export_root / '.gitkeep'
        if not export_root.is_dir() or not any(export_root.iterdir()):
            logger.warning(
                'Frontend export missing at %s. Run: python manage.py build_frontend',
                export_root,
            )
            return
        meta_path = export_root / 'BUILD_META.json'
        if meta_path.is_file():
            logger.info('Serving frontend build (%s)', meta_path.read_text(encoding='utf-8').strip())
        else:
            logger.warning(
                'Frontend export at %s has no BUILD_META.json; run python manage.py build_frontend',
                export_root,
            )
