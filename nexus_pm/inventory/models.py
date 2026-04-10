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
    created_by = models.ForeignKey('inventory.InventoryUser', on_delete=models.SET_NULL, null=True, blank=True)

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
    created_by = models.ForeignKey('inventory.InventoryUser', on_delete=models.SET_NULL, null=True, blank=True)

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
    acknowledged_by = models.ForeignKey('inventory.InventoryUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_alerts')
    resolved_by = models.ForeignKey('inventory.InventoryUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')

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
    created_by = models.ForeignKey('inventory.InventoryUser', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} rented to {self.rented_to} ({self.quantity})"

class StandardLimit(models.Model):
    value = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Standard Limit: {self.value}"

from django.contrib.auth.hashers import make_password, check_password

class InventoryUser(models.Model):
    """
    Standalone isolated table exclusively for Inventory Management Users.
    """
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=50, default='Manager', choices=[
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('staff', 'Staff')
    ])
    email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    can_access_adjustments_page = models.BooleanField(default=True)
    can_manage_adjustments = models.BooleanField(default=True)
    can_access_serials_page = models.BooleanField(default=True)
    can_manage_serials = models.BooleanField(default=True)
    can_access_limits_page = models.BooleanField(default=True)
    can_manage_limits = models.BooleanField(default=True)
    can_access_alerts_page = models.BooleanField(default=True)
    can_manage_alerts = models.BooleanField(default=True)
    can_access_rentals_page = models.BooleanField(default=True)
    can_manage_rentals = models.BooleanField(default=True)
    can_access_shortage_page = models.BooleanField(default=True)
    can_manage_shortage_exports = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self.save()
        
    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    class Meta:
        verbose_name = "Inventory User"
        verbose_name_plural = "Inventory Users"

    @property
    def display_name(self):
        return self.username

    @property
    def initials(self):
        return self.username[:2].upper() if self.username else "??"

    @property
    def avatar_color(self):
        colors = ['#6366f1', '#8b5cf6', '#ec4899', '#f43f5e', '#f97316', '#14b8a6', '#0ea5e9']
        idx = sum(ord(c) for c in self.username) % len(colors) if self.username else 0
        return colors[idx]
    @property
    def is_authenticated(self):
        return True
        
    @property
    def is_anonymous(self):
        return False

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_project_manager(self):
        # We simulate manager access for both Inventory Managers and Admins
        return self.role in ['admin', 'manager']


class InventoryNotification(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ('stock_in', 'Stock In'),
        ('stock_out', 'Stock Out'),
        ('procurement_request', 'Procurement Request'),
        ('inventory_action', 'Inventory Action'),
    ]

    recipient = models.ForeignKey('inventory.InventoryUser', on_delete=models.CASCADE, related_name='inventory_notifications')
    sender = models.ForeignKey('inventory.InventoryUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_inventory_notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPE_CHOICES, default='inventory_action')
    title = models.CharField(max_length=200)
    message = models.TextField()
    target_url = models.CharField(max_length=300, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} -> {self.recipient.username}"
