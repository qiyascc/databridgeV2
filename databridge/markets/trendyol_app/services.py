import requests
import json
import uuid
import logging
from urllib.parse import quote
from django.utils import timezone
from sentence_transformers import SentenceTransformer, util
from collections import defaultdict
from PyMultiDictionary import MultiDictionary
from functools import lru_cache
import time

from .models import TrendyolAPIConfig, TrendyolProduct

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT = 15
MAX_RETRIES = 3
RETRY_DELAY = 1

class TrendyolAPI:
    """Base class for Trendyol API operations with retry mechanism"""
    
    def __init__(self, config: TrendyolAPIConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Basic {self.config.api_key}",
            "User-Agent": f"{self.config.seller_id} - SelfIntegration",
            "Content-Type": "application/json"
        })
    
    def _make_request(self, method, endpoint, **kwargs):
        """Generic request method with retry logic"""
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        kwargs.setdefault('timeout', DEFAULT_TIMEOUT)
        
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == MAX_RETRIES - 1:
                    logger.error(f"API request failed after {MAX_RETRIES} attempts: {str(e)}")
                    raise
                logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                time.sleep(RETRY_DELAY * (attempt + 1))
    
    def get(self, endpoint, params=None):
        return self._make_request('GET', endpoint, params=params)
    
    def post(self, endpoint, data):
        return self._make_request('POST', endpoint, json=data)


class TrendyolCategoryFinder:
    """Handles category discovery and attribute management"""
    
    def __init__(self, api_client: TrendyolAPI):
        self.api = api_client
        self.model = SentenceTransformer('emrecan/bert-base-turkish-cased-mean-nli-stsb-tr')
        self.dictionary = MultiDictionary()
        self._category_cache = None
        self._attribute_cache = {}
    
    @property
    def category_cache(self):
        if self._category_cache is None:
            self._category_cache = self._fetch_all_categories()
        return self._category_cache
    
    def _fetch_all_categories(self):
        """Fetch all categories from Trendyol API"""
        try:
            data = self.api.get("product/product-categories")
            return data.get('categories', [])
        except Exception as e:
            logger.error(f"Failed to fetch categories: {str(e)}")
            raise Exception("Failed to load categories. Please check your API credentials and try again.")
    
    @lru_cache(maxsize=128)
    def get_category_attributes(self, category_id):
        """Get attributes for a specific category with caching"""
        try:
            data = self.api.get(f"product/product-categories/{category_id}/attributes")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch attributes for category {category_id}: {str(e)}")
            raise Exception(f"Failed to load attributes for category {category_id}")
    
    def find_best_category(self, search_term):
        """Find the most relevant category for a given search term"""
        try:
            categories = self.category_cache
            if not categories:
                raise ValueError("Empty category list received from API")
            
            all_matches = self._find_all_possible_matches(search_term, categories)
            
            if exact_match := self._find_exact_match(search_term, all_matches):
                return exact_match
            
            if all_matches:
                return self._select_best_match(search_term, all_matches)['id']
            
            leaf_categories = self._get_all_leaf_categories(categories)
            if leaf_categories:
                return self._select_best_match(search_term, leaf_categories)['id']
            
            suggestions = self._get_category_suggestions(search_term, categories)
            raise ValueError(f"No exact match found. Closest categories:\n{suggestions}")
            
        except Exception as e:
            logger.error(f"Category search failed for '{search_term}': {str(e)}")
            raise
    
    def _find_all_possible_matches(self, search_term, categories):
        """Find all possible matches including synonyms"""
        search_terms = {search_term.lower()}
        
        try:
            synonyms = self.dictionary.synonym('tr', search_term.lower())
            search_terms.update(synonyms[:5])
        except Exception as e:
            logger.debug(f"Couldn't fetch synonyms: {str(e)}")
        
        matches = []
        for term in search_terms:
            matches.extend(self._find_matches_for_term(term, categories))
        
        # Deduplicate while preserving order
        seen_ids = set()
        return [m for m in matches if not (m['id'] in seen_ids or seen_ids.add(m['id']))]
    
    def _find_matches_for_term(self, term, categories):
        """Recursively find matches in category tree"""
        matches = []
        term_lower = term.lower()
        
        for cat in categories:
            cat_name_lower = cat['name'].lower()
            
            if term_lower == cat_name_lower or term_lower in cat_name_lower:
                if not cat.get('subCategories'):
                    matches.append(cat)
            
            if cat.get('subCategories'):
                matches.extend(self._find_matches_for_term(term, cat['subCategories']))
        
        return matches
    
    def _find_exact_match(self, search_term, matches):
        """Check for exact name matches"""
        search_term_lower = search_term.lower()
        for match in matches:
            if search_term_lower == match['name'].lower():
                return match['id']
        return None
    
    def _select_best_match(self, search_term, candidates):
        """Select best match using semantic similarity"""
        search_embedding = self.model.encode(search_term, convert_to_tensor=True)
        
        for candidate in candidates:
            candidate_embedding = self.model.encode(candidate['name'], convert_to_tensor=True)
            candidate['similarity'] = util.cos_sim(search_embedding, candidate_embedding).item()
        
        candidates_sorted = sorted(candidates, key=lambda x: x['similarity'], reverse=True)
        
        logger.info(f"Top 3 matches for '{search_term}':")
        for i, candidate in enumerate(candidates_sorted[:3], 1):
            logger.info(f"{i}. {candidate['name']} (Similarity: {candidate['similarity']:.2f})")
        
        return candidates_sorted[0]
    
    def _get_all_leaf_categories(self, categories):
        """Get all leaf categories (categories without children)"""
        leaf_categories = []
        self._collect_leaf_categories(categories, leaf_categories)
        return leaf_categories
    
    def _collect_leaf_categories(self, categories, result):
        """Recursively collect leaf categories"""
        for cat in categories:
            if not cat.get('subCategories'):
                result.append(cat)
            else:
                self._collect_leaf_categories(cat['subCategories'], result)
    
    def _get_category_suggestions(self, search_term, categories, top_n=3):
        """Generate user-friendly suggestions"""
        leaf_categories = self._get_all_leaf_categories(categories)
        
        search_embedding = self.model.encode(search_term, convert_to_tensor=True)
        for cat in leaf_categories:
            cat_embedding = self.model.encode(cat['name'], convert_to_tensor=True)
            cat['similarity'] = util.cos_sim(search_embedding, cat_embedding).item()
        
        sorted_cats = sorted(leaf_categories, key=lambda x: x['similarity'], reverse=True)
        
        suggestions = []
        for i, cat in enumerate(sorted_cats[:top_n], 1):
            suggestions.append(f"{i}. {cat['name']} (Similarity: {cat['similarity']:.2f}, ID: {cat['id']})")
        
        return "\n".join(suggestions)


class TrendyolProductManager:
    """Handles product creation and management"""
    
    def __init__(self, api_client: TrendyolAPI):
        self.api = api_client
        self.category_finder = TrendyolCategoryFinder(api_client)
    
    def get_brand_id(self, brand_name):
        """Find brand ID by name"""
        encoded_name = quote(brand_name)
        try:
            brands = self.api.get(f"product/brands/by-name?name={encoded_name}")
            if isinstance(brands, list) and brands:
                return brands[0]['id']
            raise ValueError(f"Brand not found: {brand_name}")
        except Exception as e:
            logger.error(f"Brand search failed for '{brand_name}': {str(e)}")
            raise
    
    def create_product(self, product_data):
        """Create a new product on Trendyol"""
        try:
            category_id = self.category_finder.find_best_category(product_data.category_name)
            brand_id = self.get_brand_id(product_data.brand_name)
            attributes = self._get_sample_attributes(category_id)
            
            payload = self._build_product_payload(product_data, category_id, brand_id, attributes)
            
            logger.info("Submitting product creation request...")
            response = self.api.post(f"product/sellers/{self.api.config.seller_id}/products", payload)
            
            return response.get('batchRequestId')
        except Exception as e:
            logger.error(f"Product creation failed: {str(e)}")
            raise
    
    def check_batch_status(self, batch_id):
        """Check the status of a batch operation"""
        try:
            return self.api.get(f"product/sellers/{self.api.config.seller_id}/products/batch-requests/{batch_id}")
        except Exception as e:
            logger.error(f"Failed to check batch status: {str(e)}")
            raise
    
    def _build_product_payload(self, product, category_id, brand_id, attributes):
        from config.utils import apply_price_configuration, apply_stock_configuration
        """Construct the complete product payload"""
        return {
            "items": [{
                "barcode": product.barcode,
                "title": product.title,
                "productMainId": product.product_main_id,
                "brandId": brand_id,
                "categoryId": category_id,
                "quantity": apply_stock_configuration(product.quantity),
                "stockCode": product.stock_code,
                "description": product.description,
                "currencyType": product.currency_type,
                "listPrice": float(apply_price_configuration(product.price)) + 10,
                "salePrice": float(apply_price_configuration(product.price)),
                "vatRate": product.vat_rate,
                "images": [{"url": product.image_url}],
                "attributes": attributes
            }]
        }
    
    def _get_sample_attributes(self, category_id):
        """Generate sample attributes for a category"""
        attributes = []
        category_attrs = self.category_finder.get_category_attributes(category_id)
        
        for attr in category_attrs.get('categoryAttributes', []):
            # Skip attributes with empty attributeValues array when custom values are not allowed
            if not attr.get('attributeValues') and not attr.get('allowCustom'):
                continue
                
            attribute = {
                "attributeId": attr['attribute']['id'],
                "attributeName": attr['attribute']['name']
            }
            
            if attr.get('attributeValues') and len(attr['attributeValues']) > 0:
                if not attr['allowCustom']:
                    attribute["attributeValueId"] = attr['attributeValues'][0]['id']
                    attribute["attributeValue"] = attr['attributeValues'][0]['name']
                else:
                    attribute["customAttributeValue"] = f"Sample {attr['attribute']['name']}"
            elif attr.get('allowCustom'):
                attribute["customAttributeValue"] = f"Sample {attr['attribute']['name']}"
            else:
                continue
            
            attributes.append(attribute)
        
        return attributes


def get_active_api_config():
    try:
        return TrendyolAPIConfig.objects.filter(is_active=True).first()
    except:
        return None


def create_trendyol_product(product):
    config = get_active_api_config()
    if not config:
        logger.error("No active Trendyol API config found")
        product.set_batch_status('failed', 'No active Trendyol API config found')
        return
    
    try:
        api = TrendyolAPI(config)
        product_manager = TrendyolProductManager(api)
        
        batch_id = product_manager.create_product(product)
        
        product.batch_id = batch_id
        product.batch_status = 'processing'
        product.status_message = 'Product creation initiated'
        product.last_check_time = timezone.now()
        product.save()
        
        return batch_id
        
    except Exception as e:
        logger.error(f"Failed to create product on Trendyol: {str(e)}")
        product.set_batch_status('failed', f"Error: {str(e)}")
        return None


def check_product_batch_status(product):
    if not product.batch_id:
        return
    
    config = get_active_api_config()
    if not config:
        logger.error("No active Trendyol API config found")
        return
    
    try:
        api = TrendyolAPI(config)
        product_manager = TrendyolProductManager(api)
        
        status_data = product_manager.check_batch_status(product.batch_id)
        
        items = status_data.get('items', [])
        if not items:
            product.set_batch_status('processing', 'Waiting for processing')
            return
        
        item = items[0]
        status = item.get('status')
        
        if status == 'SUCCESS':
            product.set_batch_status('completed', 'Product created successfully')
        elif status == 'ERROR':
            product.set_batch_status('failed', f"Error: {item.get('failureReasons', 'Unknown error')}")
        else:
            product.set_batch_status('processing', f"Status: {status}")
        
    except Exception as e:
        logger.error(f"Failed to check batch status: {str(e)}")
        product.last_check_time = timezone.now()
        product.save(update_fields=['last_check_time'])


def check_pending_products():
    products = TrendyolProduct.objects.filter(
        batch_id__isnull=False,
        batch_status__in=['pending', 'processing']
    )
    
    for product in products:
        if product.needs_status_check():
            logger.info(f"Checking status for product {product.id}: {product.title}")
            check_product_batch_status(product)