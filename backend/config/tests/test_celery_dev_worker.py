import os
from unittest import mock

from django.test import SimpleTestCase, override_settings

from config.celery_dev_worker import should_start_dev_celery_worker


class ShouldStartDevCeleryWorkerTests(SimpleTestCase):
    @override_settings(CELERY_AUTO_START_WORKER=True, CELERY_TASK_ALWAYS_EAGER=False)
    def test_disabled_when_reloader_parent_process(self):
        with mock.patch.dict(os.environ, {'RUN_MAIN': 'false'}, clear=False):
            self.assertFalse(
                should_start_dev_celery_worker(use_reloader=True),
            )

    @override_settings(CELERY_AUTO_START_WORKER=True, CELERY_TASK_ALWAYS_EAGER=False)
    def test_enabled_when_reloader_child_process(self):
        with mock.patch.dict(os.environ, {'RUN_MAIN': 'true'}, clear=False):
            self.assertTrue(
                should_start_dev_celery_worker(use_reloader=True),
            )

    @override_settings(CELERY_AUTO_START_WORKER=True, CELERY_TASK_ALWAYS_EAGER=False)
    def test_enabled_with_noreload(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('RUN_MAIN', None)
            self.assertTrue(
                should_start_dev_celery_worker(use_reloader=False),
            )

    @override_settings(CELERY_AUTO_START_WORKER=False, CELERY_TASK_ALWAYS_EAGER=False)
    def test_disabled_when_setting_off(self):
        self.assertFalse(
            should_start_dev_celery_worker(use_reloader=False),
        )

    @override_settings(CELERY_AUTO_START_WORKER=True, CELERY_TASK_ALWAYS_EAGER=True)
    def test_disabled_when_eager_tasks(self):
        self.assertFalse(
            should_start_dev_celery_worker(use_reloader=False),
        )

    @override_settings(CELERY_AUTO_START_WORKER=True, CELERY_TASK_ALWAYS_EAGER=False)
    def test_disabled_for_production_settings_module(self):
        with mock.patch.dict(
            os.environ,
            {'DJANGO_SETTINGS_MODULE': 'config.settings.production', 'RUN_MAIN': 'true'},
            clear=False,
        ):
            self.assertFalse(
                should_start_dev_celery_worker(use_reloader=True),
            )
