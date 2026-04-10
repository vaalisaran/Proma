from django.db import models
from products.models import Product
from django.contrib.auth import get_user_model

User = get_user_model()

class InventoryAdjustment(models.Model):
    ADJUSTMENT_TYPE_CHOICES = [
        ('manual', 'Manual'),
        ('automated', 'Automated'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='adjustments')
    adjustment_type = models.CharField(max_length=10, choices=ADJUSTMENT_TYPE_CHOICES)
    quantity = models.IntegerField()
    reason = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.adjustment_type} adjustment for {self.product.name} ({self.quantity})"

class SerialNumber(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('sold', 'Sold'),
        ('returned', 'Returned'),
        ('damaged', 'Damaged'),
    ]

    serial_number = models.CharField(max_length=100, unique=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='serial_numbers')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='available')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.serial_number} - {self.product.name} ({self.status})"

class QuantityLimit(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='quantity_limit')
    limit_quantity = models.PositiveIntegerField(help_text="Alert will be triggered when quantity reaches this limit")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.product.name} - Limit: {self.limit_quantity}"

    class Meta:
        verbose_name = "Quantity Limit"
        verbose_name_plural = "Quantity Limits"

class Alert(models.Model):
    ALERT_TYPE_CHOICES = [
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('limit_reached', 'Limit Reached'),
    ]
    
    ALERT_STATUS_CHOICES = [
        ('active', 'Active'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    status = models.CharField(max_length=15, choices=ALERT_STATUS_CHOICES, default='active')
    message = models.TextField()
    current_quantity = models.PositiveIntegerField()
    limit_quantity = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_alerts')
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')

    def __str__(self):
        return f"{self.product.name} - {self.get_alert_type_display()} ({self.status})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Alert"
        verbose_name_plural = "Alerts"

class Rental(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='rentals')
    quantity = models.PositiveIntegerField()
    rented_to = models.CharField(max_length=255)
    reason = models.TextField(blank=True, null=True)
    rental_date = models.DateField()
    rental_time = models.TimeField()
    return_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} rented to {self.rented_to} ({self.quantity})"

class StandardLimit(models.Model):
    value = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Standard Limit: {self.value}"
