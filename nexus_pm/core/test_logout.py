import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from accounts.views import logout_view

factory = RequestFactory()
request = factory.get('/accounts/logout/')
middleware = SessionMiddleware(lambda r: None)
middleware.process_request(request)

request.session['inv_user_id'] = 1
request.session.save()

from django.contrib.auth.models import AnonymousUser
request.user = AnonymousUser()

response = logout_view(request)

print("Status code:", response.status_code)
print("Redirect URL:", response.url)
print("Session inv_user_id:", request.session.get('inv_user_id'))
