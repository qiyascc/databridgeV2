from django.urls import path
from scraper_apps.lcwaikiki.product_api import views

app_name = 'lcwaikiki_product_api'

urlpatterns = [
    # Admin action URLs
    path('update-product-data/', views.update_product_data, name='update_product_data'),
    
    # API endpoints
    path('products/', views.ProductListAPIView.as_view(), name='product_list'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<int:pk>/sizes/', views.product_size_availability, name='product_size_availability'),
    path('cities/', views.city_list, name='city_list'),
    path('stores/', views.store_list, name='store_list'),
]