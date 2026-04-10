from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import AuditLog

User = get_user_model()

class AuditAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = APIClient()
        self.client.login(username='testuser', password='testpass')
        self.log = AuditLog.objects.create(
            user=self.user,
            action='Test action',
            model_name='TestModel',
            object_id=1,
            changes='{}'
        )

    def test_list_audit_logs(self):
        url = reverse('audit-logs')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
