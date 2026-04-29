from django.apps import AppConfig


class MasterDataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.master_data'

    def ready(self):
        __import__('apps.master_data.signals')
