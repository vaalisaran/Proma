import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth import logout
from django.contrib.auth.models import AnonymousUser

factory = RequestFactory()
request = factory.get('/')
middleware = SessionMiddleware(lambda r: None)
middleware.process_request(request)

request.session['inv_user_id'] = 123
request.session.save()
old_session_key = request.session.session_key

request.user = AnonymousUser()

logout(request)

print("Old key:", old_session_key)
print("New key:", request.session.session_key)
print("Session contents:", dict(request.session))
