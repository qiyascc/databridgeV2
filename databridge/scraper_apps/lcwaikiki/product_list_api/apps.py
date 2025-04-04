from django.apps import AppConfig
from django.db.models.signals import post_migrate
from datetime import datetime

class ProductSitemapConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scraper_apps.lcwaikiki.product_list_api'
    
    def ready(self):
        # Uygulama başladığında çalışacak kodlar
        from django.conf import settings
        import django_apscheduler.jobstores
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        
        try:
            # Schedule task
            scheduler = BackgroundScheduler()
            from scraper_apps.lcwaikiki.product_list_api.tasks import fetch_product_list_data
            
            scheduler.add_job(
                fetch_product_list_data,
                trigger=IntervalTrigger(hours=16),
                id='fetch_product_list_job',
                replace_existing=True
                # next_run_time=datetime.now()
            )
            
            post_migrate.connect(self.initial_fetch, sender=self)
            
            scheduler.start()
        except Exception as e:
            print(f"Scheduler başlatılırken hata: {str(e)}")
    
    def initial_fetch(self, sender, **kwargs):
        from scraper_apps.lcwaikiki.product_list_api.tasks import fetch_product_list_data
        

        fetch_product_list_data()