from django.urls import path
from .views import (
    CityConfigurationListView, CityConfigurationCreateView, CityConfigurationUpdateView,
    PriceConfigurationUpdateView, StockConfigurationUpdateView
)

urlpatterns = [
    # City Configuration URLs
    path('city/', CityConfigurationListView.as_view(), name='city_config_list'),
    path('city/add/', CityConfigurationCreateView.as_view(), name='city_config_add'),
    path('city/<str:pk>/edit/', CityConfigurationUpdateView.as_view(), name='city_config_edit'),
    
    # Price Configuration URLs
    path('price/edit/', PriceConfigurationUpdateView.as_view(), name='price_config_edit'),
    
    # Stock Configuration URLs
    path('stock/edit/', StockConfigurationUpdateView.as_view(), name='stock_config_edit'),
]