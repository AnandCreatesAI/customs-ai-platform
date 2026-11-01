import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Build the Next.js static export into frontend/out for Django to serve.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-npm-install',
            action='store_true',
            help='Do not run npm install before building.',
        )

    def handle(self, *args, **options):
        project_root = Path(settings.PROJECT_ROOT)
        frontend_dir = project_root / 'frontend'
        package_json = frontend_dir / 'package.json'
        if not package_json.is_file():
            raise CommandError(f'Missing {package_json}')

        if not options['skip_npm_install']:
            node_modules = frontend_dir / 'node_modules'
            if not node_modules.is_dir():
                self.stdout.write('Running npm install in frontend/…')
                self._run(['npm', 'install'], frontend_dir)

        self.stdout.write('Running npm run build (static export) in frontend/…')
        self._run(['npm', 'run', 'build'], frontend_dir)

        export_root = Path(settings.FRONTEND_EXPORT_ROOT)
        required = [
            export_root / 'index.html',
            export_root / 'login.html',
            export_root / 'dashboard.html',
            export_root / 'dashboard' / 'employee-space.html',
        ]
        missing = [str(path.relative_to(project_root)) for path in required if not path.is_file()]
        if missing:
            raise CommandError(
                'Static export is incomplete. Missing: ' + ', '.join(missing),
            )

        meta = {
            'built_at': datetime.now(timezone.utc).isoformat(),
            'export_root': str(export_root),
        }
        meta_path = export_root / 'BUILD_META.json'
        meta_path.write_text(json.dumps(meta, indent=2) + '\n', encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'Frontend build OK → {export_root}'))

    def _run(self, cmd: list[str], cwd: Path) -> None:
        try:
            subprocess.run(cmd, cwd=cwd, check=True)
        except subprocess.CalledProcessError as exc:
            raise CommandError(f'Command failed ({exc.returncode}): {" ".join(cmd)}') from exc
        except FileNotFoundError as exc:
            raise CommandError('npm was not found on PATH.') from exc
