from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Category, Product
from django.contrib.auth import get_user_model

User = get_user_model()

class ProductsAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = APIClient()
        self.client.login(username='testuser', password='testpass')
        self.category = Category.objects.create(name='Test Category')

    def test_create_category(self):
        url = reverse('categories')
        data = {
            'name': 'New Category',
            'description': 'Category description',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Category.objects.count(), 2)

    def test_list_categories(self):
        url = reverse('categories')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_create_product(self):
        url = reverse('products')
        data = {
            'name': 'New Product',
            'category': self.category.id,
            'sku': 'NP001',
            'price': '9.99',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 1)

    def test_list_products(self):
        Product.objects.create(name='Existing Product', category=self.category, sku='EP001', price=5.00)
        url = reverse('products')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
