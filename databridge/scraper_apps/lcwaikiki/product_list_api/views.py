from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from scraper_apps.lcwaikiki.product_list_api.models import ProductListSource, ProductUrl
from scraper_apps.lcwaikiki.product_list_api.serializers import (
    ProductUrlListSerializer, FilteredProductUrlSerializer, OnlyUrlsSerializer
)
from scraper_apps.lcwaikiki.product_list_api.tasks import fetch_product_list_data
import logging

logger = logging.getLogger(__name__)

def update_product_list(request):
    try:
        result = fetch_product_list_data()
        
        if result:
            messages.success(request, "Ürün listesi başarıyla güncellendi.")
        else:
            messages.warning(request, "Ürün listesi güncellenirken bazı sorunlar oluştu. Lütfen loglara bakın.")
    except Exception as e:
        logger.error(f"Ürün listesi güncellenirken hata oluştu: {str(e)}")
        messages.error(request, f"Ürün listesi güncellenirken hata oluştu: {str(e)}")
    
    # Admin product list sayfasına yönlendir
    return redirect(reverse('admin:product_list_api_productlistsource_changelist'))

@api_view(['GET'])
def product_list_api(request):
    try:
        # Source filtresi kontrolü
        source_filter = request.query_params.get('source', None)
        
        if source_filter:
            try:
                # Sayısal ID ile filtreleme deneyin
                if source_filter.isdigit():
                    source_id = int(source_filter)
                    # Önce ID ile arayın, bulunamazsa URL ile arayın
                    try:
                        source = ProductListSource.objects.get(id=source_id)
                    except ProductListSource.DoesNotExist:
                        # URL içinde ID geçiyorsa onu bulmaya çalışın
                        sources = ProductListSource.objects.filter(url__contains=f"Products-{source_id}")
                        if sources.exists():
                            source = sources.first()
                        else:
                            return Response({"error": f"Source ID {source_id} bulunamadı"}, 
                                            status=status.HTTP_404_NOT_FOUND)
                else:
                    # URL olarak arayın
                    source = ProductListSource.objects.get(url=source_filter)
                    
                products = ProductUrl.objects.filter(source=source)
                serializer = FilteredProductUrlSerializer(products, many=True)
                return Response({"product_adress": serializer.data})
            except ProductListSource.DoesNotExist:
                return Response({"error": f"Source bulunamadı: {source_filter}"}, 
                                status=status.HTTP_404_NOT_FOUND)
        else:
            # Tüm ürünleri listele
            products = ProductUrl.objects.all()
            serializer = ProductUrlListSerializer(products, many=True)
            return Response({"product_adress": serializer.data})
    except Exception as e:
        logger.error(f"API hata: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def product_list_only_urls_api(request):
    try:
        # Source filtresi kontrolü
        source_filter = request.query_params.get('source', None)
        
        if source_filter:
            try:
                # Sayısal ID ile filtreleme deneyin
                if source_filter.isdigit():
                    source_id = int(source_filter)
                    # Önce ID ile arayın, bulunamazsa URL ile arayın
                    try:
                        source = ProductListSource.objects.get(id=source_id)
                    except ProductListSource.DoesNotExist:
                        # URL içinde ID geçiyorsa onu bulmaya çalışın
                        sources = ProductListSource.objects.filter(url__contains=f"Products-{source_id}")
                        if sources.exists():
                            source = sources.first()
                        else:
                            return Response({"error": f"Source ID {source_id} bulunamadı"}, 
                                            status=status.HTTP_404_NOT_FOUND)
                else:
                    # URL olarak arayın
                    source = ProductListSource.objects.get(url=source_filter)
                    
                products = ProductUrl.objects.filter(source=source)
            except ProductListSource.DoesNotExist:
                return Response({"error": f"Source bulunamadı: {source_filter}"}, 
                                status=status.HTTP_404_NOT_FOUND)
        else:
            # Tüm ürünleri listele
            products = ProductUrl.objects.all()
            
        serializer = OnlyUrlsSerializer(products, many=True)
        return Response({"product_adress": serializer.data})
    except Exception as e:
        logger.error(f"API hata: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)