from django.db.models import Q

from .models import KnowledgeBaseNote, Notification, SystemSettings


def system_settings(request):
    try:
        settings = SystemSettings.get_settings()
        return {"sys_settings": settings}
    except Exception:
        return {}


from django.contrib.auth import get_user_model

User = get_user_model()


def notifications_count(request):
    if request.user.is_authenticated and isinstance(request.user, User):
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        return {"unread_count": count}
    return {}


def notes_count(request):
    if request.user.is_authenticated and isinstance(request.user, User):
        if request.user.is_admin:
            count = KnowledgeBaseNote.objects.count()
        else:
            count = (
                KnowledgeBaseNote.objects.filter(
                    Q(project__managers=request.user)
                    | Q(project__members=request.user)
                    | Q(access_rights__user=request.user, access_rights__can_view=True)
                )
                .distinct()
                .count()
            )
        return {"notes_count": count}
    return {}


def sidebar_projects(request):
    from .models import Project
    if request.user.is_authenticated:
        if request.user.is_admin:
            projects = Project.objects.all().only('id', 'name', 'project_id')
        else:
            projects = Project.objects.filter(
                Q(managers=request.user) | Q(members=request.user)
            ).distinct().only('id', 'name', 'project_id')
        return {"sidebar_projects": projects}
    return {}
