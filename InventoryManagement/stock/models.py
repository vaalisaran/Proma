from django.db import models
from products.models import Product
from django.contrib.auth import get_user_model

User = get_user_model()

class StockEntry(models.Model):
    ENTRY_TYPE_CHOICES = [
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('transfer', 'Transfer'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_entries')
    quantity = models.PositiveIntegerField()
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPE_CHOICES)
    location_from = models.CharField(max_length=100, blank=True, null=True)
    location_to = models.CharField(max_length=100, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.get_entry_type_display()} - {self.product.name} ({self.quantity})"
