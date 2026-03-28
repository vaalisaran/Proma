from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('project_manager', 'Project Manager'),
        ('member', 'Member'),
        ('student', 'Student'),
    ]

    MODULE_CHOICES = [
        ('electronics', 'Electronics'),
        ('mechanical', 'Mechanical'),
        ('optics', 'Optics'),
        ('simulation', 'Simulation'),
        ('software', 'Software'),
        ('general', 'General'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    team = models.CharField(max_length=20, choices=MODULE_CHOICES, default='general')
    avatar_color = models.CharField(max_length=7, default='#6366f1')
    nickname = models.CharField(max_length=50, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_project_manager(self):
        return self.role == 'project_manager'

    @property
    def is_student(self):
        return self.role == 'student'

    @property
    def display_name(self):
        if self.nickname:
            return self.nickname
        return self.get_full_name() or self.username

    @property
    def initials(self):
        name = self.get_full_name()
        if name:
            parts = name.split()
            return ''.join(p[0].upper() for p in parts[:2])
        return self.username[:2].upper()
