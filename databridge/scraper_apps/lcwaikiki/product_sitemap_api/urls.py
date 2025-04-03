from django.urls import path
from scraper_apps.lcwaikiki.product_sitemap_api.views import sitemap_api

urlpatterns = [
    path('', sitemap_api, name='sitemap_api'),
]