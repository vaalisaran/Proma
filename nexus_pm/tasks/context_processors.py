from django.db.models import Q
from .models import SystemSettings, Notification, KnowledgeBaseNote

def system_settings(request):
    try:
        settings = SystemSettings.get_settings()
        return {'sys_settings': settings}
    except Exception:
        return {}

from django.contrib.auth import get_user_model
User = get_user_model()

def notifications_count(request):
    if request.user.is_authenticated and isinstance(request.user, User):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return {'unread_count': count}
    return {}

def notes_count(request):
    if request.user.is_authenticated and isinstance(request.user, User):
        if request.user.is_admin:
            count = KnowledgeBaseNote.objects.count()
        else:
            count = KnowledgeBaseNote.objects.filter(
                Q(project__manager=request.user) |
                Q(project__members=request.user) |
                Q(access_rights__user=request.user, access_rights__can_view=True)
            ).distinct().count()
        return {'notes_count': count}
    return {}
