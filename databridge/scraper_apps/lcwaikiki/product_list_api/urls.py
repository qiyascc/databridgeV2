from django.urls import path
from scraper_apps.lcwaikiki.product_list_api.views import (
    product_list_api, 
    product_list_only_urls_api
)

urlpatterns = [
    path('full/', product_list_api, name='product_list_api'),
    path('only-urls/', product_list_only_urls_api, name='product_list_only_urls_api'),
]