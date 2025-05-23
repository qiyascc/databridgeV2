# tasks.py
import logging
import requests
import json
import re
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.conf import settings
from django.utils import timezone
from urllib.parse import urlparse
from .models import Product, ProductSize, CityStock, StoreStock
from .utils import get_random_proxy, get_random_user_agent

logger = logging.getLogger(__name__)

DEFAULT_CITY_ID = "865"
INVENTORY_API_URL = "https://www.lcw.com/tr-TR/TR/ajax/Model/GetStoreInventoryMultiple"
MAX_WORKERS = 5  # Number of threads for parallel processing
BATCH_SIZE = 100  # Number of URLs to process in each batch

class ProductScraper:
    def __init__(self):
        self.session = requests.Session()
        self.max_retries = 3
        self.retry_delay = 5
        self.proxy = get_random_proxy()
        self.headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.lcw.com/',
        }

    def fetch_product_page(self, url):
        for attempt in range(1, self.max_retries + 1):
            try:
                proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
                response = self.session.get(
                    url,
                    headers=self.headers,
                    proxies=proxies,
                    timeout=30,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    return response.text
                elif response.status_code == 403:
                    logger.warning(f"Access denied (403) for {url}, attempt {attempt}")
                    if attempt == self.max_retries:
                        return None
                    # Rotate proxy and user agent for next attempt
                    self.proxy = get_random_proxy()
                    self.headers['User-Agent'] = get_random_user_agent()
                else:
                    logger.warning(f"HTTP {response.status_code} for {url}, attempt {attempt}")
                    response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error for {url}, attempt {attempt}: {str(e)}")
                if attempt == self.max_retries:
                    return None
                time.sleep(self.retry_delay * attempt)
        return None

    def fetch_inventory(self, product_option_size_ref, referer_url):
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.post(
                    INVENTORY_API_URL,
                    headers={
                        'User-Agent': get_random_user_agent(),
                        'Content-Type': 'application/json',
                        'Referer': referer_url
                    },
                    data=json.dumps({
                        "cityId": DEFAULT_CITY_ID,
                        "countyIds": [],
                        "urunOptionSizeRef": str(product_option_size_ref)
                    }),
                    proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                    timeout=30
                )
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 403:
                    logger.warning(f"Inventory access denied (403), attempt {attempt}")
                    if attempt == self.max_retries:
                        return None
                    # Rotate proxy and user agent for next attempt
                    self.proxy = get_random_proxy()
                    self.headers['User-Agent'] = get_random_user_agent()
                else:
                    logger.warning(f"Inventory HTTP {response.status_code}, attempt {attempt}")
            except Exception as e:
                logger.error(f"Error fetching inventory (attempt {attempt}): {str(e)}")
                if attempt == self.max_retries:
                    return None
                time.sleep(self.retry_delay * attempt)
        return None

    def parse_product_page(self, html, url, source):
        try:
            json_data = self.extract_json_data(html)
            if not json_data:
                logger.error(f"No JSON data found for {url}")
                return None

            product_prices = json_data.get('ProductPrices', {})
            price = float(product_prices.get('Price', 0)) if product_prices.get('Price') else 0
            discount_ratio = float(product_prices.get('DiscountRatio', 0)) if product_prices.get('DiscountRatio') else 0

            product_data = {
                "url": url,
                "title": json_data.get('PageTitle', ''),
                "category": json_data.get('CategoryName', ''),
                "color": json_data.get('Color', ''),
                "price": price,
                "discount_ratio": discount_ratio,
                "in_stock": json_data.get('IsInStock', False),
                "images": [
                    img_url for pic in json_data.get('Pictures', [])
                    for img_size in ['ExtraMedium600', 'ExtraMedium800', 'MediumImage', 'SmallImage']
                    if (img_url := pic.get(img_size))
                ],
                "timestamp": timezone.now(),
                "status": "success",
                "source": source
            }

            return product_data, json_data.get('ProductSizes', [])
        except Exception as e:
            logger.error(f"Error parsing product page {url}: {str(e)}")
            return None

    def extract_json_data(self, html):
        script_tags = re.findall(r'<script.*?>.*?cartOperationViewModel\s*=\s*({.*?});.*?</script>', html, re.DOTALL)
        
        for script in script_tags:
            try:
                pattern = r'cartOperationViewModel\s*=\s*({.*?});'
                match = re.search(pattern, script, re.DOTALL)
                if match:
                    json_str = match.group(1).strip()
                    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    return json.loads(json_str)
            except Exception as e:
                logger.error(f"JSON parsing error: {str(e)}")
                continue
        
        logger.warning("No valid JSON data found")
        return None

def scrape_product(url, source):
    scraper = ProductScraper()
    html = scraper.fetch_product_page(url)
    if not html:
        # Mark product as failed if we couldn't fetch it
        Product.objects.update_or_create(
            url=url,
            defaults={
                'status': 'failed',
                'timestamp': timezone.now(),
                'source': source
            }
        )
        return None

    parsed_data = scraper.parse_product_page(html, url, source)
    if not parsed_data:
        return None

    product_data, product_sizes = parsed_data
    
    # Create or update product
    product, created = Product.objects.update_or_create(
        url=url,
        defaults=product_data
    )

    # Process sizes
    for size_data in product_sizes:
        size_info = {
            "size_name": size_data.get('Size', {}).get('Value', ''),
            "size_id": size_data.get('Size', {}).get('SizeId', ''),
            "size_general_stock": size_data.get('Stock', 0),
            "product_option_size_reference": size_data.get('UrunOptionSizeRef', 0),
            "barcode_list": size_data.get('BarcodeList', [])
        }

        size, _ = ProductSize.objects.update_or_create(
            product=product,
            size_name=size_info['size_name'],
            defaults=size_info
        )

        # Fetch inventory for sizes with stock
        if size_info['size_general_stock'] > 0:
            inventory_data = scraper.fetch_inventory(size_info['product_option_size_reference'], url)
            if inventory_data:
                process_inventory_data(size, inventory_data, url)

    return product

def process_inventory_data(size, inventory_data, referer_url):
    # Clear existing inventory data for this size
    CityStock.objects.filter(product_size=size).delete()

    city_stocks = {}
    
    for store in inventory_data.get('storeInventoryInfos', []):
        city_id = str(store.get('StoreCityId'))
        city_name = store.get('StoreCityName')
        
        if city_id not in city_stocks:
            city_stock = CityStock.objects.create(
                product_size=size,
                city_id=city_id,
                city_name=city_name,
                stock=0
            )
            city_stocks[city_id] = city_stock
        else:
            city_stock = city_stocks[city_id]
        
        # Create store entry
        StoreStock.objects.create(
            city_stock=city_stock,
            store_code=store.get('StoreCode', ''),
            store_name=store.get('StoreName', ''),
            store_address={
                "location_with_words": store.get('Address', ''),
                "location_with_coordinants": [
                    store.get('Lattitude', ''),
                    store.get('Longitude', '')
                ]
            },
            store_phone=store.get('StorePhone', ''),
            store_county=store.get('StoreCountyName', ''),
            stock=store.get('Quantity', 0)
        )
        
        # Update city stock total
        city_stock.stock += store.get('Quantity', 0)
        city_stock.save()
    
    # Update size general stock (sum of all city stocks)
    if city_stocks:
        size.size_general_stock = sum(cs.stock for cs in city_stocks.values())
        size.save()

def fetch_product_urls(source_url):
    try:
        base_url = getattr(settings, 'BASE_API_URL', 'http://localhost:8000')
        api_url = f"{base_url.rstrip('/')}/api/{settings.CURRENT_API_VERSION}/lcwaikiki/product-list/only-urls/?source={source_url}"
        
        response = requests.get(api_url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return [item['url'] for item in data.get('product_adress', [])]
        else:
            logger.error(f"Failed to fetch product URLs: HTTP {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error fetching product URLs: {str(e)}")
        return []

def process_batch(urls, source_url):
    """Process a batch of URLs with multiple threads"""
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for url in urls:
            futures.append(executor.submit(scrape_product, url, source_url))
        
        success_count = 0
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    success_count += 1
            except Exception as e:
                logger.error(f"Error processing product: {str(e)}")
        
        return success_count

def fetch_sitemap_urls():
    """Fetch URLs from sitemap API"""
    try:
        sitemap_url = f"/api/{settings.CURRENT_API_VERSION}/lcwaikiki/product-sitemap/"
        base_url = getattr(settings, 'BASE_API_URL', 'http://localhost:8000')
        full_url = f"{base_url.rstrip('/')}{sitemap_url}"
        
        response = requests.get(full_url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get('urls', [])
        else:
            logger.error(f"Failed to fetch sitemap URLs: HTTP {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error fetching sitemap URLs: {str(e)}")
        return []

def update_products():
    """Main function to update all products"""
    logger.info("Starting product update process")
    
    # Fetch sitemap URLs
    sitemap_urls = fetch_sitemap_urls()
    if not sitemap_urls:
        logger.error("No sitemap URLs available")
        return False
    
    total_processed = 0
    
    try:
        for sitemap_url_data in sitemap_urls:
            source_url = sitemap_url_data.get("url")
            if not source_url:
                continue
                
            logger.info(f"Processing product list from: {source_url}")
            
            # Fetch all product URLs for this source
            product_urls = fetch_product_urls(source_url)
            if not product_urls:
                logger.warning(f"No product URLs found for {source_url}")
                continue
            
            # Process in batches to avoid memory issues
            for i in range(0, len(product_urls), BATCH_SIZE):
                batch = product_urls[i:i + BATCH_SIZE]
                success_count = process_batch(batch, source_url)
                total_processed += success_count
                logger.info(f"Processed batch: {success_count}/{len(batch)} successful")
            
            logger.info(f"Finished processing {len(product_urls)} products from {source_url}")
        
        logger.info(f"Product update completed. Total processed: {total_processed}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating products: {str(e)}", exc_info=True)
        return False

def clean_old_products(days=30):
    """Clean up products older than specified days"""
    try:
        cutoff_date = timezone.now() - timedelta(days=days)
        old_products = Product.objects.filter(timestamp__lt=cutoff_date)
        count = old_products.count()
        old_products.delete()
        logger.info(f"Cleaned up {count} products older than {days} days")
        return count
    except Exception as e:
        logger.error(f"Error cleaning old products: {str(e)}")
        return 0