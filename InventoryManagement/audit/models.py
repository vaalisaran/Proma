from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    model_name = models.CharField(max_length=255)
    object_id = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    changes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user} {self.action} on {self.model_name}({self.object_id}) at {self.timestamp}"

    @staticmethod
    def log(user, action, instance, changes=None):
        AuditLog.objects.create(
            user=user,
            action=action,
            model_name=instance.__class__.__name__,
            object_id=instance.pk,
            changes=changes or ''
        )
