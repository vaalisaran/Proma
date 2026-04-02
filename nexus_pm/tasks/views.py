from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.utils import timezone
from .models import Project, Task, Comment, Notification, BugReport, CalendarEvent
from .forms import ProjectForm, TaskForm, CommentForm, BugReportForm, CalendarEventForm
from .decorators import manager_or_admin_required, admin_required
from accounts.models import User
import json


def create_notification(recipient, sender, notif_type, title, message, task=None, project=None):
    if recipient and sender and recipient != sender:
        Notification.objects.create(
            recipient=recipient, sender=sender,
            notification_type=notif_type, title=title, message=message,
            task=task, project=project,
        )


# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    user = request.user
    if user.is_admin:
        import os
        from django.conf import settings
        db_size = 0
        db_path = settings.DATABASES['default'].get('NAME')
        if db_path and os.path.exists(db_path):
            db_size = os.path.getsize(db_path) / (1024 * 1024)
            
        projects = Project.objects.all()
        stats = {
            'total_projects':   projects.count(),
            'active_projects':  projects.filter(status='active').count(),
            'total_users':      User.objects.count(),
            'db_size_mb':       f"{db_size:.2f}",
            'deletion_reqs':    projects.filter(Q(deletion_requested_by_admin=True) | Q(deletion_requested_by_pm=True)).exclude(deletion_requested_by_admin=True, deletion_requested_by_pm=True).count()
        }
        return render(request, 'tasks/admin_dashboard.html', {'stats': stats, 'projects': projects.order_by('-updated_at')[:6]})

    elif user.is_project_manager:
        projects = Project.objects.filter(Q(manager=user) | Q(members=user)).distinct()
        tasks    = Task.objects.filter(Q(project__in=projects) | Q(assigned_to=user)).distinct()
    else:
        projects = Project.objects.filter(members=user)
        tasks    = Task.objects.filter(Q(project__in=projects) | Q(assigned_to=user)).distinct()

    my_tasks      = Task.objects.filter(assigned_to=user).exclude(status='done')
    overdue_tasks = [t for t in my_tasks if t.is_overdue]
    due_today     = [t for t in my_tasks if t.due_date == timezone.now().date()]
    notifications = Notification.objects.filter(recipient=user, is_read=False)[:5]

    # Bugs assigned to or reported by the user
    my_bugs = BugReport.objects.filter(
        Q(assigned_to=user) | Q(reported_by=user)
    ).exclude(status__in=['resolved','closed']).distinct()[:5]

    stats = {
        'total_projects':   projects.count(),
        'active_projects':  projects.filter(status='active').count(),
        'total_tasks':      tasks.count(),
        'my_open_tasks':    my_tasks.count(),
        'overdue_count':    len(overdue_tasks),
        'completed_tasks':  tasks.filter(status='done').count(),
        'my_open_bugs':     BugReport.objects.filter(assigned_to=user).exclude(status__in=['resolved','closed']).count(),
    }
    context = {
        'stats': stats,
        'recent_tasks': tasks.order_by('-updated_at')[:8],
        'overdue_tasks': overdue_tasks[:5],
        'due_today': due_today,
        'notifications': notifications,
        'projects': projects.order_by('-updated_at')[:6],
        'my_bugs': my_bugs,
    }
    return render(request, 'tasks/dashboard.html', context)


# ─── PROJECTS ─────────────────────────────────────────────────────────────────

@login_required
def project_list(request):
    user          = request.user
    module_filter = request.GET.get('module', '')
    status_filter = request.GET.get('status', '')
    search        = request.GET.get('q', '')

    if user.is_admin:
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(Q(manager=user) | Q(members=user)).distinct()

    if module_filter:
        projects = projects.filter(module=module_filter)
    if status_filter:
        projects = projects.filter(status=status_filter)
    if search:
        projects = projects.filter(Q(name__icontains=search) | Q(description__icontains=search))

    from django.core.paginator import Paginator
    paginator = Paginator(projects.order_by('-created_at'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'tasks/project_list.html', {
        'projects': page_obj,
        'page_obj': page_obj,
        'module_choices': Project.MODULE_CHOICES,
        'status_choices': Project.STATUS_CHOICES,
        'module_filter': module_filter,
        'status_filter': status_filter,
        'search': search,
    })


@login_required
@manager_or_admin_required
def project_create(request):
    form = ProjectForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        project = form.save(commit=False)
        project.created_by = request.user
        project.save()
        form.save_m2m()
        
        # Notify project manager if assigned
        if project.manager and project.manager != request.user:
            create_notification(
                project.manager, request.user, 'project_update',
                f'You were assigned as Project Manager: {project.name}',
                f'{request.user.display_name} assigned you as the manager of project "{project.name}".',
                project=project
            )
            
        # Notify all assigned members
        for member in project.members.all():
            create_notification(
                member, request.user, 'project_update',
                f'You were added to project: {project.name}',
                f'{request.user.display_name} added you as a member of "{project.name}".',
                project=project
            )
        messages.success(request, f'Project "{project.name}" created successfully.')
        return redirect('tasks:project_detail', pk=project.pk)
    return render(request, 'tasks/project_form.html', {
        'form': form, 'title': 'New Project', 'action': 'Create Project'
    })


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    
    if request.user.is_admin:
        messages.error(request, 'Admins cannot view inside projects.')
        return redirect('tasks:project_list')

    if not (project.members.filter(pk=request.user.pk).exists() or project.manager == request.user):
        messages.error(request, 'You do not have access to this project.')
        return redirect('tasks:project_list')

    tasks = project.tasks.all().select_related('assigned_to', 'created_by')

    # Kanban data
    kanban = {
        'todo':        tasks.filter(status='todo'),
        'in_progress': tasks.filter(status='in_progress'),
        'review':      tasks.filter(status='review'),
        'done':        tasks.filter(status='done'),
        'blocked':     tasks.filter(status='blocked'),
    }

    # Filters
    status_filter   = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    assignee_filter = request.GET.get('assignee', '')
    type_filter     = request.GET.get('type', '')
    view_mode       = request.GET.get('view', 'list')

    filtered_tasks = tasks
    if status_filter:   filtered_tasks = filtered_tasks.filter(status=status_filter)
    if priority_filter: filtered_tasks = filtered_tasks.filter(priority=priority_filter)
    if assignee_filter: filtered_tasks = filtered_tasks.filter(assigned_to_id=assignee_filter)
    if type_filter:     filtered_tasks = filtered_tasks.filter(task_type=type_filter)

    return render(request, 'tasks/project_detail.html', {
        'project':          project,
        'tasks':            filtered_tasks,
        'kanban':           kanban,
        'members':          project.members.all(),
        'bugs':             project.bug_reports.all()[:5],
        'status_choices':   Task.STATUS_CHOICES,
        'priority_choices': Task.PRIORITY_CHOICES,
        'type_choices':     Task.TYPE_CHOICES,
        'status_filter':    status_filter,
        'priority_filter':  priority_filter,
        'assignee_filter':  assignee_filter,
        'type_filter':      type_filter,
        'view_mode':        view_mode,
    })


@login_required
@manager_or_admin_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    old_members = set(project.members.values_list('pk', flat=True))
    form = ProjectForm(request.POST or None, instance=project, user=request.user)
    if request.method == 'POST' and form.is_valid():
        project = form.save()
        # Notify newly added members
        new_members = set(project.members.values_list('pk', flat=True))
        added_pks = new_members - old_members
        for member in User.objects.filter(pk__in=added_pks):
            create_notification(
                member, request.user, 'project_update',
                f'You were added to project: {project.name}',
                f'{request.user.display_name} added you as a member of "{project.name}".',
                project=project
            )
        messages.success(request, f'Project "{project.name}" updated.')
        return redirect('tasks:project_detail', pk=project.pk)
    return render(request, 'tasks/project_form.html', {
        'form': form, 'title': f'Edit — {project.name}',
        'action': 'Save Changes', 'project': project
    })


@login_required
@manager_or_admin_required
def project_members(request, pk):
    """Dedicated page to manage who is on a project."""
    project = get_object_or_404(Project, pk=pk)
    all_users = User.objects.filter(is_active=True).order_by('first_name', 'username')
    current_member_ids = set(project.members.values_list('pk', flat=True))

    if request.method == 'POST':
        action   = request.POST.get('action')
        user_id  = request.POST.get('user_id')
        if action and user_id:
            target = get_object_or_404(User, pk=user_id)
            if action == 'add':
                project.members.add(target)
                create_notification(
                    target, request.user, 'project_update',
                    f'Added to project: {project.name}',
                    f'{request.user.display_name} added you to project "{project.name}".',
                    project=project
                )
                messages.success(request, f'{target.display_name} added to the project.')
            elif action == 'remove':
                if target == project.manager:
                    messages.error(request, 'Cannot remove the project manager from members.')
                else:
                    project.members.remove(target)
                    messages.success(request, f'{target.display_name} removed from the project.')
        return redirect('tasks:project_members', pk=pk)

    return render(request, 'tasks/project_members.html', {
        'project': project,
        'all_users': all_users,
        'current_member_ids': current_member_ids,
    })


@login_required
@manager_or_admin_required
def project_delete(request, pk):
    from datetime import timedelta
    from django.utils import timezone
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action', 'request_deletion')
        name = project.name
        
        if action == 'request_deletion':
            project.deletion_requested_at = timezone.now()
            if request.user.is_admin:
                project.deletion_requested_by_admin = True
                project.save()
                messages.info(request, f'Project "{name}" deletion requested. Waiting for Project Manager approval.')
                if project.manager:
                    create_notification(project.manager, request.user, 'project_update', 'Project Deletion Requested', f'Admin {request.user.display_name} has requested to delete project "{name}". Please approve.', project=project)
            elif request.user.is_project_manager and project.manager == request.user:
                project.deletion_requested_by_pm = True
                project.save()
                messages.info(request, f'Project "{name}" deletion requested. Waiting for Admin approval.')
                for admin in User.objects.filter(role='admin'):
                    create_notification(admin, request.user, 'project_update', 'Project Deletion Requested', f'PM {request.user.display_name} has requested to delete project "{name}". Please approve.', project=project)
        
        elif action == 'cancel_deletion':
            if request.user.is_admin and project.deletion_requested_by_admin:
                project.deletion_requested_by_admin = False
                project.deletion_requested_at = None
                project.save()
                messages.info(request, f'Deletion request for "{name}" cancelled.')
            elif request.user.is_project_manager and project.manager == request.user and project.deletion_requested_by_pm:
                project.deletion_requested_by_pm = False
                project.deletion_requested_at = None
                project.save()
                messages.info(request, f'Deletion request for "{name}" cancelled.')
                
        elif action == 'approve_deletion':
            if request.user.is_admin and project.deletion_requested_by_pm:
                project.delete()
                messages.success(request, f'Project "{name}" fully deleted.')
                return redirect('tasks:project_list')
            elif request.user.is_project_manager and project.manager == request.user and project.deletion_requested_by_admin:
                project.delete()
                messages.success(request, f'Project "{name}" fully deleted.')
                return redirect('tasks:project_list')
                
        elif action == 'force_delete':
            if request.user.is_admin and project.deletion_requested_by_admin and project.deletion_requested_at:
                if timezone.now() > project.deletion_requested_at + timedelta(days=30):
                    project.delete()
                    messages.success(request, f'Project "{name}" was force deleted.')
                    return redirect('tasks:project_list')
                else:
                    messages.error(request, 'You can only force delete after 30 days of requesting.')
                    
        return redirect('tasks:project_list')
        
    # Check if 30 days have passed for force delete
    from datetime import timedelta
    from django.utils import timezone
    can_force_delete = False
    if request.user.is_admin and project.deletion_requested_by_admin and project.deletion_requested_at:
        if timezone.now() > project.deletion_requested_at + timedelta(days=30):
            can_force_delete = True

    return render(request, 'tasks/confirm_delete.html', {
        'obj': project, 'obj_type': 'Project', 'can_force_delete': can_force_delete
    })


# ─── TASKS ────────────────────────────────────────────────────────────────────

@login_required
def task_list(request):
    user            = request.user
    status_filter   = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    search          = request.GET.get('q', '')
    my_only         = request.GET.get('mine', '')
    project_filter  = request.GET.get('project', '')

    if user.is_admin:
        messages.error(request, 'Admins do not have access to tasks.')
        return redirect('tasks:dashboard')
        
    tasks = Task.objects.filter(
        Q(project__members=user) |
        Q(project__manager=user) |
        Q(assigned_to=user)
    ).distinct()

    if my_only:         tasks = tasks.filter(assigned_to=user)
    if status_filter:   tasks = tasks.filter(status=status_filter)
    if priority_filter: tasks = tasks.filter(priority=priority_filter)
    if project_filter:  tasks = tasks.filter(project_id=project_filter)
    if search:          tasks = tasks.filter(Q(title__icontains=search) | Q(description__icontains=search))

    # Projects for filter dropdown
    if user.is_admin:
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(Q(manager=user) | Q(members=user)).distinct()

    from django.core.paginator import Paginator
    task_qs = tasks.select_related('project', 'assigned_to').order_by('-updated_at')
    
    # We might want to sort by project if my_tasks is active for better regroup logic, 
    # but the instructions ask for standardized 10 item pagination, so we preserve default order.
    if my_only:
        task_qs = tasks.select_related('project', 'assigned_to').order_by('project', '-updated_at')
        
    paginator = Paginator(task_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'tasks/task_list.html', {
        'tasks':            page_obj,
        'page_obj':         page_obj,
        'status_choices':   Task.STATUS_CHOICES,
        'priority_choices': Task.PRIORITY_CHOICES,
        'projects':         projects,
        'status_filter':    status_filter,
        'priority_filter':  priority_filter,
        'project_filter':   project_filter,
        'search':           search,
        'my_only':          my_only,
        'my_tasks':         my_only,   # alias used by template
    })


@login_required
@manager_or_admin_required
def task_create(request):
    project_id = request.GET.get('project')
    project    = get_object_or_404(Project, pk=project_id) if project_id else None
    form       = TaskForm(request.POST or None, user=request.user, project=project)

    if request.method == 'POST' and form.is_valid():
        task = form.save(commit=False)
        task.created_by = request.user
        task.save()
        if task.assigned_to and task.assigned_to != request.user:
            create_notification(
                task.assigned_to, request.user, 'task_assigned',
                f'New task assigned: {task.title}',
                f'{request.user.display_name} assigned you a task in "{task.project.name}".',
                task=task, project=task.project
            )
        messages.success(request, f'Task "{task.title}" created.')
        return redirect('tasks:task_detail', pk=task.pk)
    return render(request, 'tasks/task_form.html', {
        'form': form, 'title': 'New Task', 'action': 'Create Task', 'project': project
    })


@login_required
def task_detail(request, pk):
    task     = get_object_or_404(Task, pk=pk)
    comments = task.comments.select_related('author').all()
    subtasks = task.subtasks.select_related('assigned_to').all()
    comment_form = CommentForm()

    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.task   = task
            comment.author = request.user
            comment.save()
            if task.assigned_to and task.assigned_to != request.user:
                create_notification(
                    task.assigned_to, request.user, 'comment_added',
                    f'New comment on: {task.title}',
                    f'{request.user.display_name} commented on your task.',
                    task=task, project=task.project
                )
            messages.success(request, 'Comment posted.')
            return redirect('tasks:task_detail', pk=pk)

    return render(request, 'tasks/task_detail.html', {
        'task': task, 'comments': comments,
        'subtasks': subtasks, 'comment_form': comment_form,
    })


@login_required
@manager_or_admin_required
def task_edit(request, pk):
    task         = get_object_or_404(Task, pk=pk)
    old_assignee = task.assigned_to
    form         = TaskForm(request.POST or None, instance=task, user=request.user, project=task.project)
    if request.method == 'POST' and form.is_valid():
        task = form.save()
        if task.assigned_to and task.assigned_to != old_assignee:
            create_notification(
                task.assigned_to, request.user, 'task_assigned',
                f'Task assigned to you: {task.title}',
                f'{request.user.display_name} assigned you a task.',
                task=task, project=task.project
            )
        messages.success(request, f'Task "{task.title}" updated.')
        return redirect('tasks:task_detail', pk=task.pk)
    return render(request, 'tasks/task_form.html', {
        'form': form, 'title': 'Edit Task', 'action': 'Save Changes', 'task': task
    })


@login_required
@manager_or_admin_required
def task_delete(request, pk):
    task    = get_object_or_404(Task, pk=pk)
    project = task.project
    if request.method == 'POST':
        task.delete()
        messages.success(request, 'Task deleted.')
        return redirect('tasks:project_detail', pk=project.pk)
    return render(request, 'tasks/confirm_delete.html', {'obj': task, 'obj_type': 'Task'})


@login_required
def task_update_status(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == 'POST':
        try:
            data       = json.loads(request.body)
            new_status = data.get('status')
            if new_status in dict(Task.STATUS_CHOICES):
                task.status = new_status
                task.save()
                return JsonResponse({'success': True, 'progress': task.project.progress})
        except Exception:
            pass
    return JsonResponse({'success': False}, status=400)


# ─── NOTIFICATIONS ────────────────────────────────────────────────────────────

@login_required
def notifications(request):
    notifs = Notification.objects.filter(recipient=request.user).select_related('sender', 'task', 'project')
    if request.GET.get('mark_all'):
        notifs.update(is_read=True)
        messages.success(request, 'All notifications marked as read.')
        return redirect('tasks:notifications')
    unread_count = notifs.filter(is_read=False).count()
    return render(request, 'tasks/notifications.html', {
        'notifications': notifs, 'unread_count': unread_count
    })


@login_required
def notification_read(request, pk):
    notif       = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    notif.save()
    if notif.task:    return redirect('tasks:task_detail',    pk=notif.task.pk)
    if notif.project: return redirect('tasks:project_detail', pk=notif.project.pk)
    return redirect('tasks:notifications')


# ─── BUGS ─────────────────────────────────────────────────────────────────────

@login_required
def bug_list(request):
    severity_filter = request.GET.get('severity', '')
    status_filter   = request.GET.get('status', '')
    project_filter  = request.GET.get('project', '')
    assigned_only   = request.GET.get('assigned_to_me', '')

    if request.user.is_admin:
        bugs = BugReport.objects.all()
    else:
        bugs = BugReport.objects.filter(
            Q(project__members=request.user) |
            Q(project__manager=request.user) |
            Q(reported_by=request.user) |
            Q(assigned_to=request.user)
        ).distinct()

    if assigned_only:   bugs = bugs.filter(assigned_to=request.user)
    if severity_filter: bugs = bugs.filter(severity=severity_filter)
    if status_filter:   bugs = bugs.filter(status=status_filter)
    if project_filter:  bugs = bugs.filter(project_id=project_filter)

    if request.user.is_admin:
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(Q(manager=request.user) | Q(members=request.user)).distinct()

    return render(request, 'tasks/bug_list.html', {
        'bugs':             bugs.select_related('project', 'reported_by', 'assigned_to').order_by('-created_at'),
        'severity_choices': BugReport.SEVERITY_CHOICES,
        'status_choices':   BugReport.STATUS_CHOICES,
        'projects':         projects,
        'severity_filter':  severity_filter,
        'status_filter':    status_filter,
        'project_filter':   project_filter,
        'assigned_only':    assigned_only,
    })


@login_required
def bug_create(request):
    form = BugReportForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        bug = form.save(commit=False)
        bug.reported_by = request.user
        bug.save()
        
        # When anybody reports a bug to a member, add it to assigned person's task list
        if bug.assigned_to:
            Task.objects.create(
                title=f"[Bug] {bug.title}",
                description=bug.description,
                project=bug.project,
                task_type='bug',
                status='todo',
                priority=bug.severity,
                assigned_to=bug.assigned_to,
                created_by=request.user
            )
        
        # Notify the person the bug is assigned to
        if bug.assigned_to and bug.assigned_to != request.user:
            create_notification(
                bug.assigned_to, request.user, 'task_assigned',
                f'Bug assigned to you: {bug.title}',
                f'{request.user.display_name} assigned you a bug report in "{bug.project.name}": {bug.title}.',
                project=bug.project,
            )
        messages.success(request, f'Bug "{bug.title}" reported.')
        return redirect('tasks:bug_detail', pk=bug.pk)
    return render(request, 'tasks/bug_form.html', {
        'form': form, 'title': 'Report a Bug', 'action': 'Submit Report'
    })


@login_required
def bug_detail(request, pk):
    bug = get_object_or_404(BugReport, pk=pk)
    return render(request, 'tasks/bug_detail.html', {'bug': bug})


@login_required
def bug_edit(request, pk):
    bug          = get_object_or_404(BugReport, pk=pk)
    
    if request.user != bug.reported_by and request.user != bug.assigned_to and not request.user.is_admin:
        messages.error(request, 'You do not have permission to edit this bug ticket.')
        return redirect('tasks:bug_detail', pk=pk)

    old_assignee = bug.assigned_to
    form = BugReportForm(request.POST or None, instance=bug, user=request.user)
    if request.method == 'POST' and form.is_valid():
        bug = form.save()
        
        # Add to assigned person's task list if assigned newly or changed
        if bug.assigned_to and bug.assigned_to != old_assignee:
            Task.objects.create(
                title=f"[Bug] {bug.title}",
                description=bug.description,
                project=bug.project,
                task_type='bug',
                status='todo',
                priority=bug.severity,
                assigned_to=bug.assigned_to,
                created_by=request.user
            )
            
        # Notify newly assigned person
        if bug.assigned_to and bug.assigned_to != old_assignee:
            create_notification(
                bug.assigned_to, request.user, 'task_assigned',
                f'Bug assigned to you: {bug.title}',
                f'{request.user.display_name} assigned you a bug report in "{bug.project.name}": {bug.title}.',
                project=bug.project,
            )
        messages.success(request, 'Bug report updated.')
        return redirect('tasks:bug_detail', pk=pk)
    return render(request, 'tasks/bug_form.html', {
        'form': form, 'title': 'Edit Bug Report', 'action': 'Save Changes', 'bug': bug
    })


# ─── CALENDAR ─────────────────────────────────────────────────────────────────

@login_required
def calendar_view(request):
    events = CalendarEvent.objects.filter(
        Q(created_by=request.user) | Q(attendees=request.user)
    ).distinct()
    events_data = [
        {
            'id':    e.pk,
            'title': e.title,
            'start': e.start_datetime.isoformat(),
            'end':   e.end_datetime.isoformat(),
            'color': e.color,
        }
        for e in events
    ]
    return render(request, 'tasks/calendar.html', {
        'events_json': json.dumps(events_data),
        'events': events.order_by('start_datetime')[:10],
        'form':   CalendarEventForm(),
    })


@login_required
def event_create(request):
    form = CalendarEventForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        event = form.save(commit=False)
        event.created_by = request.user
        event.save()
        form.save_m2m()
        messages.success(request, f'Event "{event.title}" created.')
        return redirect('tasks:calendar')
    return render(request, 'tasks/event_form.html', {
        'form': form, 'title': 'New Event', 'action': 'Create Event'
    })


# ─── REPORTS ──────────────────────────────────────────────────────────────────

@login_required
def reports(request):
    if request.user.is_admin:
        projects = Project.objects.all()
        tasks    = Task.objects.all()
    else:
        projects = Project.objects.filter(Q(manager=request.user) | Q(members=request.user)).distinct()
        tasks    = Task.objects.filter(project__in=projects)

    task_by_status   = {s: tasks.filter(status=s).count()   for s, _ in Task.STATUS_CHOICES}
    task_by_priority = {p: tasks.filter(priority=p).count() for p, _ in Task.PRIORITY_CHOICES}
    proj_by_status   = {s: projects.filter(status=s).count()   for s, _ in Project.STATUS_CHOICES}
    proj_by_module   = {m: projects.filter(module=m).count()   for m, _ in Project.MODULE_CHOICES}
    overdue_tasks    = [t for t in tasks.select_related('project', 'assigned_to') if t.is_overdue]

    # Team workload
    team_workload = []
    for username, _ in User.MODULE_CHOICES:
        members = User.objects.filter(team=username, is_active=True)
        open_tasks = Task.objects.filter(assigned_to__in=members).exclude(status='done').count()
        team_workload.append({'team': username.title(), 'open_tasks': open_tasks, 'members': members.count()})

    return render(request, 'tasks/reports.html', {
        'projects':        projects,
        'tasks':           tasks,
        'task_by_status':  task_by_status,
        'task_by_priority': task_by_priority,
        'proj_by_status':  proj_by_status,
        'proj_by_module':  proj_by_module,
        'overdue_tasks':   overdue_tasks,
        'total_tasks':     tasks.count(),
        'completed_tasks': tasks.filter(status='done').count(),
        'active_projects': projects.filter(status='active').count(),
        'team_workload':   team_workload,
    })


# ─── AJAX: Tasks for a project ────────────────────────────────────────────────

@login_required
def tasks_for_project(request):
    """Return JSON list of tasks for a given project (used by file upload & bug forms)."""
    project_id = request.GET.get('project_id')
    if not project_id:
        return JsonResponse({'tasks': []})
    tasks = Task.objects.filter(project_id=project_id).values('id', 'title').order_by('title')
    return JsonResponse({'tasks': list(tasks)})


@login_required
def project_members_api(request):
    """Return JSON list of members for a given project (used by bug form)."""
    project_id = request.GET.get('project_id')
    if not project_id:
        return JsonResponse({'members': []})
    try:
        project = Project.objects.get(pk=project_id)
    except (Project.DoesNotExist, ValueError):
        return JsonResponse({'members': []})

    member_ids = list(project.members.values_list('pk', flat=True))
    if project.manager_id:
        member_ids.append(project.manager_id)

    members = User.objects.filter(pk__in=member_ids, is_active=True).order_by('first_name', 'username')
    data = [{'id': u.pk, 'name': u.display_name} for u in members]
    return JsonResponse({'members': data})


# ─── KNOWLEDGE BASE ──────────────────────────────────────────────────────────

@login_required
def kb_list(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not request.user.is_admin:
        if not (project.members.filter(pk=request.user.pk).exists() or project.manager == request.user):
            messages.error(request, 'You do not have access to this project.')
            return redirect('tasks:project_list')
    notes = project.kb_notes.all()
    return render(request, 'tasks/kb_list.html', {'project': project, 'notes': notes})


@login_required
def kb_create(request, pk):
    project = get_object_or_404(Project, pk=pk)
    from .forms import KnowledgeBaseNoteForm
    form = KnowledgeBaseNoteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        note = form.save(commit=False)
        note.project = project
        note.author = request.user
        note.save()
        messages.success(request, 'Note created.')
        return redirect('tasks:kb_list', pk=project.pk)
    return render(request, 'tasks/kb_form.html', {'form': form, 'project': project, 'title': 'Create Note', 'action': 'Save Note'})


@login_required
def kb_detail(request, pk):
    from .models import KnowledgeBaseNote
    note = get_object_or_404(KnowledgeBaseNote, pk=pk)
    project = note.project
    if not request.user.is_admin:
        if not (project.members.filter(pk=request.user.pk).exists() or project.manager == request.user):
            messages.error(request, 'You do not have access to this note.')
            return redirect('tasks:project_list')
    return render(request, 'tasks/kb_detail.html', {'note': note, 'project': project})


@login_required
def kb_edit(request, pk):
    from .models import KnowledgeBaseNote
    note = get_object_or_404(KnowledgeBaseNote, pk=pk)
    project = note.project
    if not request.user.is_admin and request.user != note.author and project.manager != request.user:
        messages.error(request, "You can only edit your own notes or if you are the project manager.")
        return redirect('tasks:kb_detail', pk=pk)
        
    from .forms import KnowledgeBaseNoteForm
    form = KnowledgeBaseNoteForm(request.POST or None, instance=note)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Note updated.')
        return redirect('tasks:kb_detail', pk=pk)
    return render(request, 'tasks/kb_form.html', {'form': form, 'project': project, 'title': 'Edit Note', 'action': 'Update Note'})

# ─── CI/CD & RELEASES ────────────────────────────────────────────────────────
@login_required
def project_cicd(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not request.user.is_admin:
        if not (project.members.filter(pk=request.user.pk).exists() or project.manager == request.user):
            messages.error(request, 'You do not have access to this project.')
            return redirect('tasks:project_list')

    pipeline_runs = project.pipeline_runs.all()[:10]
    releases = project.releases.all()

    return render(request, 'tasks/project_cicd.html', {
        'project': project,
        'pipeline_runs': pipeline_runs,
        'releases': releases
    })
