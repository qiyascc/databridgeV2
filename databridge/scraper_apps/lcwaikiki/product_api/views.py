from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q, Count, Sum, F, OuterRef, Subquery, Exists
from django.utils import timezone

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status, filters
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView

from scraper_apps.lcwaikiki.product_api.models import (
    Product, ProductSize, Store, SizeStoreStock
)
from config.models import CityConfiguration as City
from scraper_apps.lcwaikiki.product_api.serializers import (
    ProductSerializer, ProductListSerializer
)
from scraper_apps.lcwaikiki.product_api.tasks import fetch_product_data

import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

def update_product_data(request):
    """Admin view to trigger product data update"""
    try:
        result = fetch_product_data()
        
        if result:
            messages.success(request, "Ürün verileri başarıyla güncellendi.")
        else:
            messages.warning(request, "Ürün verileri güncellenirken bazı sorunlar oluştu.")
    except Exception as e:
        logger.error(f"Error updating product data: {str(e)}")
        messages.error(request, f"Ürün verilerini güncellerken hata oluştu: {str(e)}")
    
    return redirect(reverse('admin:lcwaikiki_product_api_product_changelist'))

@api_view(['GET'])
def product_detail(request, pk):
    """Get detailed product information"""
    try:
        product = Product.objects.get(pk=pk)
        serializer = ProductSerializer(product)
        return Response(serializer.data)
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error retrieving product detail: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProductListAPIView(ListAPIView):
    """
    API view for listing products with advanced filtering
    """
    serializer_class = ProductListSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'category', 'color', 'url']
    ordering_fields = ['title', 'price', 'timestamp', 'category']
    ordering = ['-timestamp']

    def get_queryset(self):
        queryset = Product.objects.all()
        
        # Filter by URL (exact match)
        url = self.request.query_params.get('url')
        if url:
            queryset = queryset.filter(url=url)
        
        # Filter by category (partial match)
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__icontains=category)
            
        # Filter by color (partial match)
        color = self.request.query_params.get('color')
        if color:
            queryset = queryset.filter(color__icontains=color)
            
        # Filter by price range
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
            
        # Filter by discount ratio range
        min_discount = self.request.query_params.get('min_discount')
        max_discount = self.request.query_params.get('max_discount')
        if min_discount:
            queryset = queryset.filter(discount_ratio__gte=min_discount)
        if max_discount:
            queryset = queryset.filter(discount_ratio__lte=max_discount)
            
        # Filter by in_stock status
        in_stock = self.request.query_params.get('in_stock')
        if in_stock:
            in_stock_bool = in_stock.lower() == 'true'
            queryset = queryset.filter(in_stock=in_stock_bool)
            
        # Filter by status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        # Filter by updated in the last X days
        days = self.request.query_params.get('days')
        if days:
            days_ago = timezone.now() - timedelta(days=int(days))
            queryset = queryset.filter(timestamp__gte=days_ago)
            
        # Filter by size name
        size_name = self.request.query_params.get('size_name')
        if size_name:
            queryset = queryset.filter(sizes__size_name__iexact=size_name)
            
        # Filter by size availability
        size_available = self.request.query_params.get('size_available')
        if size_available:
            size_available_bool = size_available.lower() == 'true'
            if size_available_bool:
                queryset = queryset.filter(sizes__size_general_stock__gt=0)
            else:
                queryset = queryset.filter(sizes__size_general_stock=0)
            
        # Filter by city availability
        city_id = self.request.query_params.get('city_id')
        if city_id:
            city_ids = city_id.split(',')
            queryset = queryset.filter(
                sizes__store_stocks__store__city__city_id__in=city_ids
            ).distinct()
            
        # Filter by store code
        store_code = self.request.query_params.get('store_code')
        if store_code:
            store_codes = store_code.split(',')
            queryset = queryset.filter(
                sizes__store_stocks__store__store_code__in=store_codes
            ).distinct()
            
        # Filter by store phone
        store_phone = self.request.query_params.get('store_phone')
        if store_phone:
            queryset = queryset.filter(
                sizes__store_stocks__store__store_phone__icontains=store_phone
            ).distinct()
            
        # Filter by minimum store stock
        min_store_stock = self.request.query_params.get('min_store_stock')
        if min_store_stock:
            queryset = queryset.filter(
                sizes__store_stocks__stock__gte=int(min_store_stock)
            ).distinct()
        
        return queryset

@api_view(['GET'])
def city_list(request):
    """Get list of cities with product availability"""
    try:
        cities = City.objects.annotate(
            product_count=Count('stores__size_stocks__product_size__product', distinct=True)
        ).filter(product_count__gt=0).values('city_id', 'name', 'product_count')
        
        return Response(list(cities))
    except Exception as e:
        logger.error(f"Error retrieving city list: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def store_list(request):
    """Get list of stores with product availability"""
    try:
        city_id = request.query_params.get('city_id')
        
        stores_query = Store.objects.annotate(
            product_count=Count('size_stocks__product_size__product', distinct=True),
            total_stock=Sum('size_stocks__stock')
        ).filter(product_count__gt=0)
        
        if city_id:
            stores_query = stores_query.filter(city__city_id=city_id)
            
        stores = stores_query.values(
            'store_code', 'store_name', 'city__name', 'store_county',
            'store_phone', 'address', 'latitude', 'longitude',
            'product_count', 'total_stock'
        )
        
        return Response(list(stores))
    except Exception as e:
        logger.error(f"Error retrieving store list: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def product_size_availability(request, pk):
    """Get size availability for a specific product"""
    try:
        product = Product.objects.get(pk=pk)
        
        sizes = ProductSize.objects.filter(product=product).annotate(
            store_count=Count('store_stocks', filter=Q(store_stocks__stock__gt=0)),
            city_count=Count('store_stocks__store__city', distinct=True, filter=Q(store_stocks__stock__gt=0))
        ).values(
            'id', 'size_name', 'size_general_stock', 'store_count', 'city_count'
        )
        
        return Response({
            'product_id': product.id,
            'product_title': product.title,
            'sizes': list(sizes)
        })
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error retrieving product size availability: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)