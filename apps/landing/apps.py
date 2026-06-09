from django.apps import AppConfig


class LandingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.landing"
    verbose_name = "Landing Page Public"

    def ready(self):
        __import__("apps.landing.signals")
