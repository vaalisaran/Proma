from .models import SystemSettings, Notification

def system_settings(request):
    try:
        settings = SystemSettings.get_settings()
        return {'sys_settings': settings}
    except Exception:
        return {}

def notifications_count(request):
    if request.user.is_authenticated:
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return {'unread_count': count}
    return {}
