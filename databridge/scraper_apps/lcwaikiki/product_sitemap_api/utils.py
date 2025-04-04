import requests
from xml.etree import ElementTree
import logging

logger = logging.getLogger(__name__)

def fetch_and_process_sitemap():
    from .models import ProductSitemap
    try:
        config = ProductSitemap.load()
        response = requests.get(config.url, timeout=10)
        response.raise_for_status()
        
        root = ElementTree.fromstring(response.content)
        urls = [elem.text for elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
        
        # Veritabanına kaydetme (Bu örnekte sadece logluyoruz)
        logger.info(f"Bulunan URL'ler: {urls}")
        # Gerçek uygulamada burada veritabanına kaydetme işlemi yapılacak
        
    except Exception as e:
        logger.error(f"Hata oluştu: {str(e)}")