import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.urls import resolve

match = resolve('/accounts/logout/')
print("View func:", match.func)
print("View name:", match.view_name)
print("App name:", match.app_name)
print("Namespace:", match.namespace)
