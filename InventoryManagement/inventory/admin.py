from django.contrib import admin
from .models import InventoryAdjustment, SerialNumber, QuantityLimit, Alert

@admin.register(InventoryAdjustment)
class InventoryAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('product', 'adjustment_type', 'quantity', 'reason', 'timestamp', 'created_by')
    list_filter = ('adjustment_type', 'timestamp')
    search_fields = ('product__name', 'reason')

@admin.register(SerialNumber)
class SerialNumberAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'product', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('serial_number', 'product__name')

@admin.register(QuantityLimit)
class QuantityLimitAdmin(admin.ModelAdmin):
    list_display = ('product', 'limit_quantity', 'is_active', 'created_at', 'created_by')
    list_filter = ('is_active', 'created_at')
    search_fields = ('product__name', 'product__sku')
    list_editable = ('is_active',)

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('product', 'alert_type', 'status', 'current_quantity', 'limit_quantity', 'created_at')
    list_filter = ('alert_type', 'status', 'created_at')
    search_fields = ('product__name', 'message')
    readonly_fields = ('created_at', 'acknowledged_at', 'resolved_at')
    list_editable = ('status',)
