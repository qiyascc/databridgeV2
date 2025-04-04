import logging
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from .models import BatchRequest, APIConfig
from .services.trendyol_api import TrendyolAPI, TrendyolProductManager

logger = logging.getLogger(__name__)

def check_batch_status(batch_request_id):
    """Check the status of a batch request"""
    with transaction.atomic():
        batch_request = BatchRequest.objects.select_for_update().get(id=batch_request_id)
        
        # Skip completed batches
        if batch_request.status in ['COMPLETED', 'FAILED']:
            logger.info(f"Batch {batch_request.batch_id} already in final state: {batch_request.status}")
            return
        
        # Get API config
        api_config = APIConfig.objects.filter(is_default=True).first()
        if not api_config:
            logger.error("No default API configuration found")
            batch_request.error_message = "No default API configuration found"
            batch_request.save()
            return
            
        try:
            # Initialize API client
            api_client = TrendyolAPI(
                api_key=api_config.api_key,
                seller_id=api_config.seller_id,
                base_url=api_config.base_url
            )
            product_manager = TrendyolProductManager(api_client)
            
            # Check status from API
            status_data = product_manager.check_batch_status(batch_request.batch_id)
            
            # Update status
            if status_data:
                api_status = status_data.get('status', '').upper()
                if api_status in ['PROCESSING', 'COMPLETED', 'FAILED']:
                    batch_request.status = api_status
                
                # Store error message if any
                if api_status == 'FAILED' and 'failureReasons' in status_data:
                    error_details = []
                    for reason in status_data['failureReasons']:
                        error_details.append(f"{reason.get('code', '')}: {reason.get('message', '')}")
                    
                    batch_request.error_message = "\n".join(error_details)
            
            batch_request.last_checked = timezone.now()
            batch_request.save()
            
            logger.info(f"Batch {batch_request.batch_id} status updated to: {batch_request.status}")
            
            return batch_request.status
            
        except Exception as e:
            logger.error(f"Error checking batch status: {str(e)}")
            batch_request.error_message = f"Error: {str(e)}"
            batch_request.last_checked = timezone.now()
            batch_request.save()
            raise

def schedule_batch_status_checks():
    """Schedule status checks for all non-completed batch requests"""
    # Find all batches that need checking (not in final state and not checked in last 2 minutes)
    cutoff_time = timezone.now() - timedelta(minutes=2)
    pending_batches = BatchRequest.objects.filter(
        status__in=['CREATED', 'PROCESSING'],
        last_checked__lt=cutoff_time
    )
    
    count = 0
    for batch in pending_batches:
        try:
            check_batch_status(batch.id)
            count += 1
        except Exception as e:
            logger.error(f"Failed to check batch {batch.batch_id}: {str(e)}")
    
    logger.info(f"Scheduled checks completed for {count} batches")
    return count