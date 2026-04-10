import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client

client = Client()
response = client.get('/accounts/logout/')
print("Logout redirect:", response.status_code, response.url if response.status_code == 302 else '')
