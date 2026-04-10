import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client

client = Client()
response = client.get('/accounts/logout/')
print("status_code:", response.status_code)
print("url:", response.url if hasattr(response, 'url') else 'No URL')
