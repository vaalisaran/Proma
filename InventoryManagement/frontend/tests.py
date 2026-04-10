from django.test import TestCase, Client
from django.urls import reverse

class FrontendUITest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_login_page_loads(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Login")

    def test_dashboard_page_requires_login(self):
        response = self.client.get(reverse('dashboard-page'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_dashboard_page_loads_after_login(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('dashboard-page'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard Overview")

    def test_stock_in_page_requires_login(self):
        response = self.client.get(reverse('stockin-page'))
        self.assertEqual(response.status_code, 302)

    def test_stock_out_page_requires_login(self):
        response = self.client.get(reverse('stockout-page'))
        self.assertEqual(response.status_code, 302)

    def test_inventory_adjustments_page_requires_login(self):
        response = self.client.get(reverse('inventory-adjustments-page'))
        self.assertEqual(response.status_code, 302)

    def test_product_categories_page_requires_login(self):
        response = self.client.get(reverse('categories-page'))
        self.assertEqual(response.status_code, 302)

    def test_user_roles_page_requires_login(self):
        response = self.client.get(reverse('roles-page'))
        self.assertEqual(response.status_code, 302)

    def test_audit_logs_page_requires_login(self):
        response = self.client.get(reverse('audit-logs-page'))
        self.assertEqual(response.status_code, 302)
