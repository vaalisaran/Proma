from django.contrib import admin
from .models import UserProfile, Role

# Register your models here.
admin.site.register(UserProfile)
admin.site.register(Role)
