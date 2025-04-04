from django.apps import AppConfig
from django.db.models.signals import post_migrate

class ProductSitemapConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scraper_apps.lcwaikiki.product_sitemap_api'
    
    def ready(self):
        # Uygulama başladığında çalışacak kodlar
        from django.conf import settings
        import django_apscheduler.jobstores
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        
        try:
            # Schedule task
            scheduler = BackgroundScheduler()
            from scraper_apps.lcwaikiki.product_sitemap_api.tasks import fetch_sitemap_data

            from scraper_apps.lcwaikiki.product_sitemap_api.models import SitemapSource
            if not SitemapSource.objects.exists():
                SitemapSource.objects.create()
            
            scheduler.add_job(
                fetch_sitemap_data,
                trigger=IntervalTrigger(hours=12),
                id='fetch_sitemap_job',
                replace_existing=True
            )
            
            # İlk başlangıçta veriyi çek
            post_migrate.connect(self.initial_fetch, sender=self)
            
            # Scheduler'ı başlat
            scheduler.start()
        except Exception as e:
            print(f"Scheduler başlatılırken hata: {str(e)}")
    
    def initial_fetch(self, sender, **kwargs):
        from scraper_apps.lcwaikiki.product_sitemap_api.models import SitemapSource
        from scraper_apps.lcwaikiki.product_sitemap_api.tasks import fetch_sitemap_data
        
        # Eğer kayıt yoksa, default kayıt oluştur
        if not SitemapSource.objects.exists():
            SitemapSource.objects.create()
        
        # İlk veriyi çek
        fetch_sitemap_data()