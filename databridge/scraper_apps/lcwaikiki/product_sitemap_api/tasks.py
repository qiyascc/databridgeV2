import requests
import xml.etree.ElementTree as ET
import random
import logging
import time
from django.utils import timezone
from django.conf import settings
from scraper_apps.lcwaikiki.product_sitemap_api.models import SitemapSource, SitemapUrl

logger = logging.getLogger(__name__)

class SitemapScraper:
    """LCWaikiki sitemap scraper with improved proxy and user agent handling"""
    
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

    def parse_sitemap_index(self, content):
        """Parse sitemap index XML content"""
        if not content:
            return []
            
        try:
            # XML namespace
            ns = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            
            # Parse XML
            root = ET.fromstring(content)
            
            # Extract sitemap entries
            sitemap_entries = []
            for sitemap_elem in root.findall(".//sitemap:sitemap", ns):
                loc_elem = sitemap_elem.find("sitemap:loc", ns)
                lastmod_elem = sitemap_elem.find("sitemap:lastmod", ns)
                
                if loc_elem is not None and loc_elem.text:
                    url = loc_elem.text.strip()
                    lastmod = None
                    
                    if lastmod_elem is not None and lastmod_elem.text:
                        try:
                            lastmod_text = lastmod_elem.text.strip()
                            # Handle ISO format with T
                            if 'T' in lastmod_text:
                                lastmod = timezone.make_aware(
                                    timezone.datetime.fromisoformat(lastmod_text.replace('Z', '+00:00'))
                                )
                            else:
                                # Simple date format
                                lastmod = timezone.datetime.strptime(lastmod_text, "%Y-%m-%d").date()
                        except ValueError:
                            logger.warning(f"Invalid date format: {lastmod_elem.text}")
                    
                    sitemap_entries.append((url, lastmod))
            
            return sitemap_entries
            
        except ET.ParseError as e:
            logger.error(f"XML parse error: {str(e)}")
            return []

def fetch_sitemap_data():
    """Main function to fetch and update sitemap data"""
    scraper = SitemapScraper()
    
    try:
        # Get or create source
        source = SitemapSource.objects.first()
        if not source:
            source = SitemapSource.objects.create()
        
        logger.info(f"Starting sitemap fetch from: {source.url}")
        
        # Clear existing URLs
        SitemapUrl.objects.filter(source=source).delete()
        
        # Fetch sitemap content
        content = scraper.fetch(source.url)
        if not content:
            logger.error("Failed to fetch sitemap content")
            return False
        
        # Parse and store sitemap entries
        sitemap_entries = scraper.parse_sitemap_index(content)
        if not sitemap_entries:
            logger.warning("No sitemap entries found")
            return False
        
        # Create new URLs
        for url, lastmod in sitemap_entries:
            SitemapUrl.objects.create(
                source=source,
                url=url,
                last_modification=lastmod
            )
        
        # Update last fetch time
        source.last_fetch = timezone.now()
        source.save()
        
        logger.info(f"Successfully updated sitemap: {len(sitemap_entries)} entries stored")
        return True
        
    except Exception as e:
        logger.error(f"Error updating sitemap: {str(e)}", exc_info=True)
        return False