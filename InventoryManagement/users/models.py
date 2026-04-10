from django.db import models
from django.contrib.auth.models import AbstractUser, Permission

class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    permissions = models.ManyToManyField(Permission, blank=True, related_name='roles')

    def __str__(self):
        return self.name

class UserProfile(AbstractUser):
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    profile_image = models.ImageField(upload_to='user_profiles/', blank=True, null=True)

    def __str__(self):
        return self.username
