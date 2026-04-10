from django.core.management.base import BaseCommand
from django.utils import timezone
from products.models import Product
from inventory.models import QuantityLimit, Alert
from stock.models import StockEntry
from django.db.models import Sum, Q


class Command(BaseCommand):
    help = 'Check product quantities and create alerts when limits are reached'

    def handle(self, *args, **options):
        self.stdout.write("Checking product quantities and limits...")
        
        # Get all products with quantity limits
        limits = QuantityLimit.objects.filter(is_active=True)
        
        alerts_created = 0
        alerts_updated = 0
        
        for limit in limits:
            product = limit.product
            
            # Calculate current quantity
            stock_in = StockEntry.objects.filter(product=product, entry_type='in').aggregate(
                total=Sum('quantity')
            )['total'] or 0
            
            stock_out = StockEntry.objects.filter(product=product, entry_type='out').aggregate(
                total=Sum('quantity')
            )['total'] or 0
            
            current_quantity = stock_in - stock_out
            
            # Check if quantity is at or below limit
            if current_quantity <= limit.limit_quantity:
                # Check if there's already an active alert for this product and limit
                existing_alert = Alert.objects.filter(
                    product=product,
                    alert_type='limit_reached',
                    status='active'
                ).first()
                
                if existing_alert:
                    # Update existing alert if quantity changed
                    if existing_alert.current_quantity != current_quantity:
                        existing_alert.current_quantity = current_quantity
                        existing_alert.message = f"Product {product.name} quantity ({current_quantity}) has reached or fallen below the limit of {limit.limit_quantity}"
                        existing_alert.save()
                        alerts_updated += 1
                        self.stdout.write(f"Updated alert for {product.name}: {current_quantity} <= {limit.limit_quantity}")
                else:
                    # Create new alert
                    Alert.objects.create(
                        product=product,
                        alert_type='limit_reached',
                        status='active',
                        message=f"Product {product.name} quantity ({current_quantity}) has reached or fallen below the limit of {limit.limit_quantity}",
                        current_quantity=current_quantity,
                        limit_quantity=limit.limit_quantity
                    )
                    alerts_created += 1
                    self.stdout.write(f"Created alert for {product.name}: {current_quantity} <= {limit.limit_quantity}")
            else:
                # Check if there's an active alert that should be resolved
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
                    self.stdout.write(f"Resolved alert for {product.name}: {current_quantity} > {limit.limit_quantity}")
        
        # Also check for out of stock products
        all_products = Product.objects.all()
        for product in all_products:
            stock_in = StockEntry.objects.filter(product=product, entry_type='in').aggregate(
                total=Sum('quantity')
            )['total'] or 0
            
            stock_out = StockEntry.objects.filter(product=product, entry_type='out').aggregate(
                total=Sum('quantity')
            )['total'] or 0
            
            current_quantity = stock_in - stock_out
            
            if current_quantity <= 0:
                # Check if there's already an active out of stock alert
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
                    alerts_created += 1
                    self.stdout.write(f"Created out of stock alert for {product.name}")
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
                    self.stdout.write(f"Resolved out of stock alert for {product.name}")
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Alert check completed. Created: {alerts_created}, Updated: {alerts_updated}'
            )
        ) 