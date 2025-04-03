from django.urls import path, include

urlpatterns = [
    path('product-sitemap/', include('scraper_apps.lcwaikiki.product_sitemap_api.urls')),
]
