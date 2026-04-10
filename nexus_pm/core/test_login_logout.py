import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client
from inventory.models import InventoryUser

try:
    user = InventoryUser.objects.create(username='test_inv', password='123', is_active=True)
    user.set_password('123')
    user.save()
except Exception as e:
    user = InventoryUser.objects.get(username='test_inv')
    user.set_password('123')
    user.save()

client = Client()

# Verify no session initially
print("Initial session:", client.session.get('inv_user_id'))

# Login
response = client.post('/accounts/inventory_login/', {'username': 'test_inv', 'password': '123'})
print("Login redirect status:", response.status_code)
print("Login redirect url:", response.url)
print("Session after login:", client.session.get('inv_user_id'))

# Access dashboard
response = client.get('/inventory/dashboard/overview/')
print("Dashboard access status:", response.status_code)

# Logout
response = client.get('/accounts/logout/')
print("Logout redirect status:", response.status_code)
print("Logout redirect url:", response.url)
print("Session after logout:", dict(client.session))

# Access dashboard again
response = client.get('/inventory/dashboard/overview/')
print("Dashboard access after logout status:", response.status_code)
if response.status_code == 302:
    print("Dashboard redirected to:", response.url)

