from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from scraper_apps.lcwaikiki.product_sitemap_api.models import SitemapSource, SitemapUrl
from scraper_apps.lcwaikiki.product_sitemap_api.serializers import SitemapSourceSerializer
from scraper_apps.lcwaikiki.product_sitemap_api.tasks import fetch_sitemap_data
import random
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from datetime import datetime
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

def update_sitemap(request):
    try:
        source = SitemapSource.objects.first()
        if not source:
            source = SitemapSource.objects.create()
        
        fetch_sitemap_data()
        
        messages.success(request, "Sitemap başarıyla güncellendi.")
    except Exception as e:
        logger.error(f"Sitemap güncellenirken hata oluştu: {str(e)}")
        messages.error(request, f"Sitemap güncellenirken hata oluştu: {str(e)}")
    
    return redirect(reverse('admin:product_sitemap_sitemapsource_change', args=[source.id]))

@api_view(['GET'])
def sitemap_api(request):
    try:
        source = SitemapSource.objects.first()
        if not source:
            source = SitemapSource.objects.create()
        
        serializer = SitemapSourceSerializer(source)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"API hata: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)