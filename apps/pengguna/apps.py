from django.apps import AppConfig


class PenggunaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pengguna"

    def ready(self):
        # Import signal handlers saat app siap agar sinkronisasi profil pengguna tetap aktif.
        __import__('apps.pengguna.signals')
