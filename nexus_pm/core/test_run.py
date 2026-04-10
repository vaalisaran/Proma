import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import RequestFactory
from accounts.views import logout_view
from django.contrib.sessions.middleware import SessionMiddleware

factory = RequestFactory()
request = factory.get('/accounts/logout/')
SessionMiddleware(lambda r: None).process_request(request)

from django.contrib.auth.models import AnonymousUser
request.user = AnonymousUser()

response = logout_view(request)
print("status_code:", response.status_code)
print("url:", response.url)
