from django.urls import path, include

urlpatterns = [
    path('v1/', include('scraper_apps.urls')),
]
