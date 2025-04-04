from .models import PriceConfiguration, StockConfiguration

def get_active_price_config():
    """Get the active price configuration"""
    try:
        return PriceConfiguration.objects.filter(is_active=True).first()
    except PriceConfiguration.DoesNotExist:
        return None

def get_active_stock_config():
    """Get the active stock configuration"""
    try:
        return StockConfiguration.objects.filter(is_active=True).first()
    except StockConfiguration.DoesNotExist:
        return None

def apply_price_configuration(original_price):
    """Apply price configuration rules to the original price"""
    config = get_active_price_config()
    if not config or not original_price:
        return original_price
    
    if original_price < config.PRICE_THRESHOLD:
        return original_price * config.BELOW_THRESHOLD_MULTIPLIER
    else:
        return original_price * config.ABOVE_THRESHOLD_MULTIPLIER

def apply_stock_configuration(original_quantity):
    """Apply stock configuration rules to the original quantity"""
    config = get_active_stock_config()
    if not config:
        return original_quantity
    
    return config.get_mapped_quantity(original_quantity)