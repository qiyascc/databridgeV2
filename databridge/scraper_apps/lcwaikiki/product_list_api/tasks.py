import requests
import xml.etree.ElementTree as ET
import random
import logging
import time
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from scraper_apps.lcwaikiki.product_sitemap_api.models import SitemapUrl
from scraper_apps.lcwaikiki.product_list_api.models import ProductListSource, ProductUrl

logger = logging.getLogger(__name__)

class ProductListScraper:
    """LCWaikiki product XML list scraper with improved proxy and user agent handling"""
    
    # Define a list of common user agents
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPad; CPU OS 16_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Mobile/15E148 Safari/604.1'
    ]
    
    def __init__(self):
        self.session = requests.Session()
        self.max_retries = 5
        self.retry_delay = 5
        
    def _get_random_proxy(self):
        """Get a random proxy from settings"""
        if not settings.PROXY_LIST:
            return None
        return random.choice(settings.PROXY_LIST)
    
    def _get_headers(self):
        """Generate request headers with random user agent"""
        user_agent = random.choice(self.USER_AGENTS)
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.lcw.com/',
            'User-Agent': user_agent,
        }
        
    def fetch(self, url, max_proxy_attempts=None):
        """Fetch URL content with retry and proxy rotation logic"""
        if max_proxy_attempts is None:
            max_proxy_attempts = len(settings.PROXY_LIST) if settings.PROXY_LIST else 1
            
        proxy_attempts = 0
        proxies_tried = set()
        
        while proxy_attempts < max_proxy_attempts:
            # Get a proxy that hasn't been tried yet if possible
            available_proxies = [p for p in settings.PROXY_LIST if p not in proxies_tried] if settings.PROXY_LIST else [None]
            if not available_proxies:
                logger.warning("All proxies have been tried without success")
                break
                
            proxy = random.choice(available_proxies)
            proxies = {"http": proxy, "https": proxy} if proxy else None
            
            if proxy:
                proxies_tried.add(proxy)
            
            # Update headers with new random user agent for each attempt
            self.session.headers.update(self._get_headers())
            
            logger.info(f"Proxy attempt {proxy_attempts + 1}/{max_proxy_attempts}: {proxy}")
            
            # Try up to max_retries times with this proxy
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = self.session.get(
                        url, 
                        proxies=proxies, 
                        timeout=30,
                        allow_redirects=True,
                        verify=True
                    )
                    
                    if response.status_code == 200:
                        logger.info(f"Successfully fetched {url}")
                        return response.content
                    
                    elif response.status_code == 403:
                        logger.warning(f"Access denied (403) with proxy {proxy}, attempt {attempt}")
                        if attempt == self.max_retries:
                            break  # Try next proxy
                        time.sleep(self.retry_delay * attempt)  # Exponential backoff
                        
                    else:
                        logger.warning(f"HTTP {response.status_code} with proxy {proxy}, attempt {attempt}")
                        response.raise_for_status()
                        
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Request error with proxy {proxy}, attempt {attempt}: {str(e)}")
                    if attempt == self.max_retries:
                        break  # Try next proxy
                    time.sleep(self.retry_delay * attempt)  # Exponential backoff
            
            proxy_attempts += 1
        
        logger.error("All proxy attempts failed")
        return None

    def parse_product_list(self, content):
        """Parse product list XML content"""
        if not content:
            return []
            
        try:
            # Parse XML
            root = ET.fromstring(content)
            
            # Extract product URLs
            product_entries = []
            for url_elem in root.findall(".//url"):
                loc_elem = url_elem.find("loc")
                lastmod_elem = url_elem.find("lastmod")
                changefreq_elem = url_elem.find("changefreq")
                priority_elem = url_elem.find("priority")
                
                if loc_elem is not None and loc_elem.text:
                    url = loc_elem.text.strip()
                    lastmod = None
                    changefreq = None
                    priority = None
                    
                    if lastmod_elem is not None and lastmod_elem.text:
                        try:
                            lastmod_text = lastmod_elem.text.strip()
                            # Parse the date
                            lastmod = datetime.strptime(lastmod_text, "%Y-%m-%d").date()
                        except ValueError:
                            logger.warning(f"Invalid date format: {lastmod_elem.text}")
                    
                    if changefreq_elem is not None and changefreq_elem.text:
                        changefreq = changefreq_elem.text.strip()
                        
                    if priority_elem is not None and priority_elem.text:
                        priority = priority_elem.text.strip()
                    
                    product_entries.append((url, lastmod, changefreq, priority))
            
            return product_entries
            
        except ET.ParseError as e:
            logger.error(f"XML parse error: {str(e)}")
            return []

def fetch_sitemap_urls():
    """Fetch URLs from sitemap API"""
    try:
        sitemap_api_url = f"/api/{settings.CURRENTLY_API_VERSION}/lcwaikiki/product-sitemap/"
        # Get base URL from settings or use a default
        base_url = getattr(settings, 'BASE_API_URL', 'http://localhost:8000')
        
        full_url = f"{base_url.rstrip('/')}{sitemap_api_url}"
        logger.info(f"Fetching sitemap URLs from: {full_url}")
        
        response = requests.get(full_url)
        if response.status_code == 200:
            data = response.json()
            return data.get('urls', [])
        else:
            logger.error(f"Failed to fetch sitemap URLs: HTTP {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error fetching sitemap URLs: {str(e)}")
        return []

def fetch_product_list_data():
    """Main function to fetch and update product list data"""
    scraper = ProductListScraper()
    sitemap_urls = fetch_sitemap_urls()
    
    if not sitemap_urls:
        logger.error("No sitemap URLs available")
        return False
    
    try:
        total_products = 0
        
        for sitemap_url_data in sitemap_urls:
            url = sitemap_url_data.get("url")
            last_modification = sitemap_url_data.get("last_modification")
            
            if not url:
                continue
                
            logger.info(f"Processing sitemap URL: {url}")
            
            # Convert last_modification string to date object if it exists
            last_mod_date = None
            if last_modification:
                try:
                    last_mod_date = datetime.strptime(last_modification, "%Y-%m-%d").date()
                except ValueError:
                    logger.warning(f"Invalid date format: {last_modification}")
            
            # Create or update source
            source, created = ProductListSource.objects.update_or_create(
                url=url,
                defaults={
                    'last_modification': last_mod_date
                }
            )
            
            # Fetch product list content
            content = scraper.fetch(url)
            if not content:
                logger.error(f"Failed to fetch product list content from {url}")
                continue
            
            # Parse and store product entries
            product_entries = scraper.parse_product_list(content)
            if not product_entries:
                logger.warning(f"No product entries found in {url}")
                continue
            
            # Create new product URLs
            for product_url, lastmod, changefreq, priority in product_entries:
                try:
                    ProductUrl.objects.update_or_create(
                        source=source,
                        url=product_url,
                        defaults={
                            'lcw_last_modification': lastmod,
                            'change_frequency': changefreq,
                            'priority': priority
                        }
                    )
                    total_products += 1
                except Exception as e:
                    logger.error(f"Error creating product URL: {str(e)}")
            
            # Update last fetch time
            source.last_fetch = timezone.now()
            source.save()
            
            logger.info(f"Successfully processed {url}: {len(product_entries)} products stored")
        
        logger.info(f"Total products processed: {total_products}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating product list: {str(e)}", exc_info=True)
        return False