from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
def test_user(user_obj):
    import sys
    print("Testing user object:", user_obj)
    print("Type:", type(user_obj))
    print("Hasattr user:", hasattr(user_obj, 'user'))
    print("Is authenticated:", user_obj.is_authenticated)
    print("Isinstance AnonymousUser:", isinstance(user_obj, AnonymousUser))
