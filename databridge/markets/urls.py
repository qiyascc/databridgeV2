from django.urls import path, include

urlpatterns = [
    path('markets/', include('markets.trendyol_app.urls')),
]