from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Role, UserProfile

User = get_user_model()

class UsersAPITest(APITestCase):
    def setUp(self):
        self.role = Role.objects.create(name='Test Role')
        self.user = UserProfile.objects.create_user(username='testuser', password='testpass', role=self.role)
        self.client = APIClient()
        self.client.login(username='testuser', password='testpass')

    def test_create_role(self):
        url = reverse('roles')
        data = {
            'name': 'New Role',
            'description': 'Role description',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Role.objects.count(), 2)

    def test_list_roles(self):
        url = reverse('roles')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_create_user_profile(self):
        url = reverse('user-profiles')
        data = {
            'username': 'newuser',
            'password': 'newpass123',
            'role': self.role.id,
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UserProfile.objects.count(), 2)

    def test_list_user_profiles(self):
        url = reverse('user-profiles')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
