from django.db.models.signals import post_save
from django.dispatch import receiver
from stock.models import StockEntry
from inventory.models import QuantityLimit, Alert
from django.utils import timezone
from django.db.models import Sum


@receiver(post_save, sender=StockEntry)
def check_alerts_on_stock_change(sender, instance, created, **kwargs):
    """
    Check for alerts when stock entries are created or updated
    """
    if created:
        product = instance.product
        
        # Calculate current quantity for this product
        stock_in = StockEntry.objects.filter(product=product, entry_type='in').aggregate(
            total=Sum('quantity')
        )['total'] or 0
        
        stock_out = StockEntry.objects.filter(product=product, entry_type='out').aggregate(
            total=Sum('quantity')
        )['total'] or 0
        
        current_quantity = stock_in - stock_out
        
        # Check if product has a quantity limit
        try:
            limit = QuantityLimit.objects.get(product=product, is_active=True)
            
            if current_quantity <= limit.limit_quantity:
                # Check if there's already an active alert
                existing_alert = Alert.objects.filter(
                    product=product,
                    alert_type='limit_reached',
                    status='active'
                ).first()
                
                if not existing_alert:
                    # Create new alert
                    Alert.objects.create(
                        product=product,
                        alert_type='limit_reached',
                        status='active',
                        message=f"Product {product.name} quantity ({current_quantity}) has reached or fallen below the limit of {limit.limit_quantity}",
                        current_quantity=current_quantity,
                        limit_quantity=limit.limit_quantity
                    )
                else:
                    # Update existing alert
                    existing_alert.current_quantity = current_quantity
                    existing_alert.message = f"Product {product.name} quantity ({current_quantity}) has reached or fallen below the limit of {limit.limit_quantity}"
                    existing_alert.save()
            else:
                # Resolve existing alert if quantity is now above limit
                existing_alert = Alert.objects.filter(
                    product=product,
                    alert_type='limit_reached',
                    status='active'
                ).first()
                
                if existing_alert:
                    existing_alert.status = 'resolved'
                    existing_alert.resolved_at = timezone.now()
                    existing_alert.message = f"Alert resolved: {product.name} quantity ({current_quantity}) is now above limit ({limit.limit_quantity})"
                    existing_alert.save()
        
        except QuantityLimit.DoesNotExist:
            pass
        
        # Check for out of stock
        if current_quantity <= 0:
            existing_alert = Alert.objects.filter(
                product=product,
                alert_type='out_of_stock',
                status='active'
            ).first()
            
            if not existing_alert:
                Alert.objects.create(
                    product=product,
                    alert_type='out_of_stock',
                    status='active',
                    message=f"Product {product.name} is out of stock (quantity: {current_quantity})",
                    current_quantity=current_quantity
                )
        else:
            # Resolve out of stock alert if quantity is now positive
            existing_alert = Alert.objects.filter(
                product=product,
                alert_type='out_of_stock',
                status='active'
            ).first()
            
            if existing_alert:
                existing_alert.status = 'resolved'
                existing_alert.resolved_at = timezone.now()
                existing_alert.message = f"Out of stock alert resolved: {product.name} now has {current_quantity} in stock"
                existing_alert.save() 