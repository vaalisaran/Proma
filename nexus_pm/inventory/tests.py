from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import InventoryAdjustment, SerialNumber
from products.models import Product

User = get_user_model()

class InventoryAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = APIClient()
        self.client.login(username='testuser', password='testpass')
        self.product = Product.objects.create(name='Test Product', sku='TP001')

    def test_create_inventory_adjustment(self):
        url = reverse('inventory-adjustments')
        data = {
            'product': self.product.id,
            'adjustment_type': 'manual',
            'quantity': 5,
            'reason': 'Test adjustment',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(InventoryAdjustment.objects.count(), 1)

    def test_list_inventory_adjustments(self):
        InventoryAdjustment.objects.create(product=self.product, adjustment_type='manual', quantity=3, created_by=self.user)
        url = reverse('inventory-adjustments')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_serial_number(self):
        url = reverse('serial-numbers')
        data = {
            'serial_number': 'SN123456',
            'product': self.product.id,
            'status': 'available',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SerialNumber.objects.count(), 1)

    def test_list_serial_numbers(self):
        SerialNumber.objects.create(serial_number='SN0001', product=self.product)
        url = reverse('serial-numbers')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
