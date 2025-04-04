# apps.py
from django.apps import AppConfig
from django.db.models.signals import post_migrate
from datetime import datetime, timedelta
import django_apscheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

class ProductApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scraper_apps.lcwaikiki.product_api'
    
    def ready(self):
        # Schedule task
        try:
            scheduler = BackgroundScheduler()
            from scraper_apps.lcwaikiki.product_api.tasks import fetch_product_data
            
            scheduler.add_job(
                fetch_product_data,
                trigger=IntervalTrigger(hours=22),
                id='product_data_and_update_job',
                max_instances=10,
                replace_existing=True
                # next_run_time=datetime.now() + timedelta(seconds=5)
            )
            
            # post_migrate.connect(self.initial_update, sender=self)
            
            scheduler.start()
        except Exception as e:
            print(f"Scheduler error: {str(e)}")
    
    def initial_update(self, sender, **kwargs):
        from scraper_apps.lcwaikiki.product_api.tasks import fetch_product_data
        fetch_product_data()