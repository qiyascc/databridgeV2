from django.urls import path, include

urlpatterns = [
    path('lcwaikiki/', include('scraper_apps.lcwaikiki.urls')),
]
