from django.urls import path, include

urlpatterns = [
    path('product-sitemap/', include('scraper_apps.lcwaikiki.product_sitemap_api.urls')),
    path('product-list/', include('scraper_apps.lcwaikiki.product_list_api.urls')),
    path('product-data/', include('scraper_apps.lcwaikiki.product_api.urls')),
]
