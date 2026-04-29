from django.apps import AppConfig


class OperasionalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.operasional'

    def ready(self):
        __import__('apps.operasional.signals')
