from django.apps import AppConfig


class TrendyolAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'markets.trendyol_app'
    verbose_name = 'Trendyol API Entegrasyonu'
    
    def ready(self):
        from . import signals
        from .scheduler import start_scheduler