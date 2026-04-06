from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.utils import timezone
from .models import Project, Task, Comment, Notification, BugReport, CalendarEvent, ProjectModule, ModuleMember, Release, ReleaseModuleVersion
from .forms import ProjectForm, TaskForm, CommentForm, BugReportForm, CalendarEventForm, ProjectModuleForm, ReleaseForm
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

def get_visible_tasks_qs(user, tasks_qs):
    if user.is_admin:
        return tasks_qs
    return tasks_qs.filter(
        Q(module__isnull=True) |
        Q(module__members__user=user) |
        Q(project__manager=user) |
        Q(assignees=user) |
        Q(created_by=user)
    ).distinct()

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
        tasks    = get_visible_tasks_qs(user, Task.objects.filter(Q(project__in=projects) | Q(assignees=user)))
    else:
        projects = Project.objects.filter(members=user)
        tasks    = get_visible_tasks_qs(user, Task.objects.filter(Q(project__in=projects) | Q(assignees=user)))

    my_tasks      = Task.objects.filter(assignees=user).exclude(status='done')
    overdue_tasks = [t for t in my_tasks if t.is_overdue]
    due_today     = [t for t in my_tasks if t.due_date == timezone.now().date()]
    notifications = Notification.objects.filter(recipient=user, is_read=False)[:5]

    # Bugs assigned to or reported by the user
    my_bugs = BugReport.objects.filter(
        Q(assignees=user) | Q(reported_by=user)
    ).exclude(status__in=['resolved','closed']).distinct()[:5]

    stats = {
        'total_projects':   projects.count(),
        'active_projects':  projects.filter(status='active').count(),
        'total_tasks':      tasks.count(),
        'my_open_tasks':    my_tasks.count(),
        'overdue_count':    len(overdue_tasks),
        'completed_tasks':  tasks.filter(status='done').count(),
        'my_open_bugs':     BugReport.objects.filter(assignees=user).exclude(status__in=['resolved','closed']).count(),
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
        
        budget_amt = form.cleaned_data.get('budget')
        if budget_amt is not None:
            from finance.models import Budget
            Budget.objects.create(project=project, total_amount=budget_amt)
        
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

    tasks = get_visible_tasks_qs(request.user, project.tasks.all()).select_related('created_by').prefetch_related('assignees')

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
    if assignee_filter: filtered_tasks = filtered_tasks.filter(assignees__id=assignee_filter)
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
    if request.user.is_project_manager and request.user != project.manager:
        messages.error(request, 'Only the assigned project manager can edit this project.')
        return redirect('tasks:project_detail', pk=project.pk)
    old_members = set(project.members.values_list('pk', flat=True))
    form = ProjectForm(request.POST or None, instance=project, user=request.user)
    if request.method == 'POST' and form.is_valid():
        project = form.save()
        
        budget_amt = form.cleaned_data.get('budget')
        if budget_amt is not None:
            from finance.models import Budget
            budget_obj, created = Budget.objects.get_or_create(project=project)
            budget_obj.total_amount = budget_amt
            budget_obj.save()

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
        
    tasks = get_visible_tasks_qs(user, Task.objects.filter(
        Q(project__members=user) |
        Q(project__manager=user) |
        Q(assignees=user)
    ))

    if my_only:         tasks = tasks.filter(assignees=user)
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
    task_qs = tasks.select_related('project').prefetch_related('assignees').order_by('-updated_at')
    
    # We might want to sort by project if my_tasks is active for better regroup logic, 
    # but the instructions ask for standardized 10 item pagination, so we preserve default order.
    if my_only:
        task_qs = tasks.select_related('project').prefetch_related('assignees').order_by('project', '-updated_at')
        
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
    module_id  = request.GET.get('module')
    project    = get_object_or_404(Project, pk=project_id) if project_id else None
    
    initial = {}
    if module_id:
        initial['module'] = get_object_or_404(ProjectModule, pk=module_id)
        
    form = TaskForm(request.POST or None, user=request.user, project=project, initial=initial)

    if request.method == 'POST' and form.is_valid():
        task = form.save(commit=False)
        task.created_by = request.user
        task.save()
        form.save_m2m()
        for assignee in task.assignees.all():
            if assignee != request.user:
                create_notification(
                    assignee, request.user, 'task_assigned',
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
    task = get_object_or_404(Task, pk=pk)
    
    # Check visibility
    if not get_visible_tasks_qs(request.user, Task.objects.filter(pk=pk)).exists():
        messages.error(request, "You do not have permission to view this task.")
        return redirect('tasks:task_list')

    comments = task.comments.select_related('author').all()
    subtasks = task.subtasks.prefetch_related('assignees').all()
    comment_form = CommentForm()

    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.task   = task
            comment.author = request.user
            comment.save()
            for assignee in task.assignees.all():
                if assignee != request.user:
                    create_notification(
                        assignee, request.user, 'comment_added',
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
def task_edit(request, pk):
    task         = get_object_or_404(Task, pk=pk)
    
    is_pm = task.project.manager == request.user
    is_assignee = task.assignees.filter(pk=request.user.pk).exists()
    
    if task.created_by != request.user and not request.user.is_admin and not is_pm and not is_assignee:
        messages.error(request, 'Only the creator, project manager, or assignees can edit this task.')
        return redirect('tasks:task_detail', pk=pk)
        
    old_assignees = set(task.assignees.all())
    old_status = task.status
    form         = TaskForm(request.POST or None, instance=task, user=request.user, project=task.project)
    if request.method == 'POST' and form.is_valid():
        task = form.save()
        new_assignees = set(task.assignees.all())
        added_assignees = new_assignees - old_assignees
        for assignee in added_assignees:
            if assignee != request.user:
                create_notification(
                    assignee, request.user, 'task_assigned',
                    f'Task assigned to you: {task.title}',
                    f'{request.user.display_name} assigned you a task.',
                    task=task, project=task.project
                )
                
        if old_status != task.status:
            # If status changed by assignee, notify PM
            if is_assignee and not is_pm and task.project.manager:
                create_notification(
                    task.project.manager, request.user, 'project_update',
                    f'Task status updated: {task.title}',
                    f'{request.user.display_name} updated the status of task "{task.title}" to {task.get_status_display()}.',
                    task=task, project=task.project
                )
            
            # If status changed by PM (or another user), notify assignees
            if not is_assignee or is_pm:
                for assignee in task.assignees.all():
                    if assignee != request.user:
                        create_notification(
                            assignee, request.user, 'project_update',
                            f'Task status updated: {task.title}',
                            f'{request.user.display_name} updated the status of your task "{task.title}" to {task.get_status_display()}.',
                            task=task, project=task.project
                        )
                        
        messages.success(request, f'Task "{task.title}" updated.')
        return redirect('tasks:task_detail', pk=task.pk)
    return render(request, 'tasks/task_form.html', {
        'form': form, 'title': 'Edit Task', 'action': 'Save Changes', 'task': task
    })


@login_required
def task_delete(request, pk):
    task    = get_object_or_404(Task, pk=pk)
    project = task.project
    
    if task.created_by != request.user and not request.user.is_admin:
        messages.error(request, 'Only the creator of the task can delete it.')
        return redirect('tasks:task_detail', pk=pk)
        
    if request.method == 'POST':
        task.delete()
        messages.success(request, 'Task deleted.')
        return redirect('tasks:project_detail', pk=project.pk)
    return render(request, 'tasks/confirm_delete.html', {'obj': task, 'obj_type': 'Task'})


@login_required
def task_update_status(request, pk):
    task = get_object_or_404(Task, pk=pk)
    
    is_assignee = task.assignees.filter(id=request.user.id).exists()
    if not is_assignee and not request.user.is_admin:
        return JsonResponse({'success': False, 'message': 'Only the assigned person can change status.'}, status=403)
        
    if request.method == 'POST':
        try:
            data       = json.loads(request.body)
            new_status = data.get('status')
            if new_status in dict(Task.STATUS_CHOICES):
                task.status = new_status
                task.save()
                
                # Notification logic for status change
                pm = task.project.manager
                is_pm = (request.user == pm)
                
                if is_assignee and not is_pm and pm:
                    create_notification(
                        pm, request.user, 'task_updated',
                        f'Task status changed: {task.title}',
                        f'{request.user.display_name} moved task to {task.get_status_display()}.',
                        task=task, project=task.project
                    )
                elif is_pm:
                    for assignee in task.assignees.all():
                        if assignee != pm:
                            create_notification(
                                assignee, request.user, 'task_updated',
                                f'Task status changed: {task.title}',
                                f'Project Manager {pm.display_name} moved your task to {task.get_status_display()}.',
                                task=task, project=task.project
                            )
                            
                return JsonResponse({'success': True, 'progress': task.project.progress})
        except Exception:
            pass
    return JsonResponse({'success': False}, status=400)


# ─── NOTIFICATIONS ────────────────────────────────────────────────────────────

@login_required
def notifications(request):
    notifs = Notification.objects.filter(recipient=request.user).select_related('sender', 'task', 'project')
    status_filter = request.GET.get('status', 'unread')
    type_filter = request.GET.get('type', '')
    
    if request.GET.get('mark_all'):
        notifs.update(is_read=True)
        messages.success(request, 'All notifications marked as read.')
        return redirect('tasks:notifications')
        
    unread_count = notifs.filter(is_read=False).count()
    
    if status_filter == 'unread':
        notifs = notifs.filter(is_read=False)
    elif status_filter == 'read':
        notifs = notifs.filter(is_read=True)
        
    if type_filter:
        notifs = notifs.filter(notification_type=type_filter)
        
    from django.core.paginator import Paginator
    paginator = Paginator(notifs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'tasks/notifications.html', {
        'notifications': page_obj, 'page_obj': page_obj, 'unread_count': unread_count,
        'status_filter': status_filter, 'type_filter': type_filter,
        'type_choices': Notification.TYPE_CHOICES
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
            Q(assignees=request.user)
        ).distinct()

    if assigned_only:   bugs = bugs.filter(assignees=request.user)
    if severity_filter: bugs = bugs.filter(severity=severity_filter)
    if status_filter:   bugs = bugs.filter(status=status_filter)
    if project_filter:  bugs = bugs.filter(project_id=project_filter)

    if request.user.is_admin:
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(Q(manager=request.user) | Q(members=request.user)).distinct()

    return render(request, 'tasks/bug_list.html', {
        'bugs':             bugs.select_related('project', 'reported_by').prefetch_related('assignees').order_by('-created_at'),
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
        form.save_m2m()
        
        # When anybody reports a bug to a member, add it to assigned person's task list
        if bug.assignees.exists():
            new_task = Task.objects.create(
                title=f"[Bug] {bug.title}",
                description=bug.description,
                project=bug.project,
                task_type='bug',
                status='todo',
                priority=bug.severity,
                created_by=request.user
            )
            new_task.assignees.set(bug.assignees.all())
        
        # Notify the person the bug is assigned to
        for assignee in bug.assignees.all():
            if assignee != request.user:
                create_notification(
                    assignee, request.user, 'task_assigned',
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
    
    if request.user != bug.reported_by and not bug.assignees.filter(pk=request.user.pk).exists() and not request.user.is_admin:
        messages.error(request, 'You do not have permission to edit this bug ticket.')
        return redirect('tasks:bug_detail', pk=pk)

    old_assignees = set(bug.assignees.all())
    form = BugReportForm(request.POST or None, instance=bug, user=request.user)
    if request.method == 'POST' and form.is_valid():
        bug = form.save()
        
        new_assignees = set(bug.assignees.all())
        added_assignees = new_assignees - old_assignees
        
        # Add to assigned person's task list if assigned newly or changed
        if added_assignees:
            new_task = Task.objects.create(
                title=f"[Bug] {bug.title}",
                description=bug.description,
                project=bug.project,
                task_type='bug',
                status='todo',
                priority=bug.severity,
                created_by=request.user
            )
            new_task.assignees.set(added_assignees)
            
        # Notify newly assigned person
        for assignee in added_assignees:
            if assignee != request.user:
                create_notification(
                    assignee, request.user, 'task_assigned',
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
    
    # Tasks with due dates for the user
    my_tasks = Task.objects.filter(assignees=request.user, due_date__isnull=False)
    for t in my_tasks:
        events_data.append({
            'id': f'task-{t.pk}',
            'title': f'Task due: {t.title}',
            'start': t.due_date.isoformat(),
            'allDay': True,
            'color': '#ef4444' if t.is_overdue else '#3b82f6',
            'url': f'/tasks/{t.pk}/'
        })
        
    # Mix events and tasks in upcoming list
    upcoming_tasks = my_tasks.order_by('due_date')[:5]
    
    return render(request, 'tasks/calendar.html', {
        'events_json': json.dumps(events_data),
        'events': events.order_by('start_datetime')[:10],
        'upcoming_tasks': upcoming_tasks,
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
        messages.info(request, 'Reports are not available in admin mode.')
        return redirect('tasks:project_list')
    else:
        projects = Project.objects.filter(Q(manager=request.user) | Q(members=request.user)).distinct()
        tasks    = get_visible_tasks_qs(request.user, Task.objects.filter(project__in=projects))

    task_by_status   = {s: tasks.filter(status=s).count()   for s, _ in Task.STATUS_CHOICES}
    task_by_priority = {p: tasks.filter(priority=p).count() for p, _ in Task.PRIORITY_CHOICES}
    proj_by_status   = {s: projects.filter(status=s).count()   for s, _ in Project.STATUS_CHOICES}
    proj_by_module   = {m: projects.filter(module=m).count()   for m, _ in Project.MODULE_CHOICES}
    overdue_tasks    = [t for t in tasks.select_related('project').prefetch_related('assignees') if t.is_overdue]

    # Team workload
    team_workload = []
    for username, _ in User.MODULE_CHOICES:
        members = User.objects.filter(team=username, is_active=True)
        open_tasks = Task.objects.filter(assignees__in=members).exclude(status='done').count()
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
    tasks = get_visible_tasks_qs(request.user, Task.objects.filter(project_id=project_id)).values('id', 'title').order_by('title')
    return JsonResponse({'tasks': list(tasks)})

@login_required
def project_modules_api(request):
    """Return JSON list of modules for a given project (used by task form)."""
    project_id = request.GET.get('project_id')
    if not project_id:
        return JsonResponse({'modules': [], 'is_manager': False})
    project = get_object_or_404(Project, pk=project_id)
    is_manager = True if request.user == project.manager or request.user.is_admin else False
    modules = ProjectModule.objects.filter(project=project).values('id', 'name').order_by('name')
    return JsonResponse({'modules': list(modules), 'is_manager': is_manager})


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

def check_kb_access(kb, user, access_type='view'):
    if user.is_admin or kb.author == user:
        return True
    if kb.project and kb.project.manager == user:
        return True
        
    from files.models import DocumentAccessRight
    explicit = DocumentAccessRight.objects.filter(kb_note=kb, user=user).first()
    if explicit:
        if access_type == 'view': return explicit.can_view
        if access_type == 'edit': return explicit.can_edit
        if access_type == 'delete': return explicit.can_delete
        
    if access_type != 'view':
        return False
        
    if kb.module:
         return ModuleMember.objects.filter(module=kb.module, user=user).exists()
    elif kb.project:
         return kb.project.members.filter(pk=user.pk).exists()
    return False

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
    if not check_kb_access(note, request.user, 'view'):
        messages.error(request, 'You do not have access to this note.')
        return redirect('tasks:project_list')
    return render(request, 'tasks/kb_detail.html', {'note': note, 'project': project})


@login_required
def kb_edit(request, pk):
    from .models import KnowledgeBaseNote
    note = get_object_or_404(KnowledgeBaseNote, pk=pk)
    project = note.project
    if not check_kb_access(note, request.user, 'edit'):
        messages.error(request, "You do not have permission to edit this note.")
        return redirect('tasks:kb_detail', pk=pk)
        
    from .forms import KnowledgeBaseNoteForm
    form = KnowledgeBaseNoteForm(request.POST or None, instance=note)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Note updated.')
        return redirect('tasks:kb_detail', pk=pk)
    return render(request, 'tasks/kb_form.html', {'form': form, 'project': project, 'title': 'Edit Note', 'action': 'Update Note'})

@login_required
def kb_access(request, pk):
    from .models import KnowledgeBaseNote
    from files.models import DocumentAccessRight
    from accounts.models import User
    
    note = get_object_or_404(KnowledgeBaseNote, pk=pk)
    project = note.project
    
    if not (request.user.is_admin or project.manager == request.user or note.author == request.user):
        messages.error(request, 'Only managers, admins, and the author can manage access rights for this KB Note.')
        return redirect('tasks:kb_detail', pk=pk)
        
    access_rights = DocumentAccessRight.objects.filter(kb_note=note)
    all_users = User.objects.filter(is_active=True)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            user_id = request.POST.get('user_id')
            can_view = request.POST.get('can_view') == 'on'
            can_edit = request.POST.get('can_edit') == 'on'
            can_delete = request.POST.get('can_delete') == 'on'
            if user_id:
                target_user = get_object_or_404(User, pk=user_id)
                ar, created = DocumentAccessRight.objects.get_or_create(kb_note=note, user=target_user)
                ar.can_view = can_view
                ar.can_edit = can_edit
                ar.can_delete = can_delete
                ar.save()
                messages.success(request, f'Access rights updated for {target_user.display_name}.')
        elif action == 'remove':
            ar_id = request.POST.get('access_id')
            if ar_id:
                DocumentAccessRight.objects.filter(pk=ar_id).delete()
                messages.success(request, 'Access right removed.')
        return redirect('tasks:kb_access', pk=pk)
        
    return render(request, 'tasks/kb_access.html', {'note': note, 'access_rights': access_rights, 'all_users': all_users})

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

# ─── MODULES ──────────────────────────────────────────────────────────────────

@login_required
def module_list(request, pk):
    project = get_object_or_404(Project, pk=pk)
    is_pm = project.manager == request.user
    
    if not is_pm and not ModuleMember.objects.filter(module__project=project, user=request.user).exists():
        messages.error(request, 'You do not have access to the modules in this project.')
        return redirect('tasks:project_list')
        
    if is_pm:
        modules = project.modules.all()
    else:
        modules = project.modules.filter(members__user=request.user).distinct()
        
    return render(request, 'tasks/module_list.html', {'project': project, 'modules': modules})

@login_required
@manager_or_admin_required
def module_create(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = ProjectModuleForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        module = form.save(commit=False)
        module.project = project
        module.save()
        messages.success(request, f'Module "{module.name}" created.')
        return redirect('tasks:module_list', pk=project.pk)
    return render(request, 'tasks/module_form.html', {'form': form, 'project': project, 'title': 'Create Module'})

@login_required
def module_detail(request, pk):
    module = get_object_or_404(ProjectModule, pk=pk)
    project = module.project
    
    is_pm = project.manager == request.user
    is_module_member = module.members.filter(user=request.user).exists()
    
    if not is_pm and not is_module_member:
        messages.error(request, 'You do not have access to this module.')
        return redirect('tasks:project_detail', pk=project.pk)
        
    members = module.members.all()
    tasks = module.tasks.all()
    files = module.files.all()
    kbs = module.kb_notes.all()
    forum_posts = module.forum_posts.all()
    
    from .forms import ModuleForumPostForm
    forum_form = ModuleForumPostForm()
    
    if request.method == 'POST':
        forum_form = ModuleForumPostForm(request.POST)
        if forum_form.is_valid():
            post = forum_form.save(commit=False)
            post.author = request.user
            post.module = module
            post.save()
            
            # Notify members
            module_member_users = [m.user for m in module.members.all() if m.user != request.user]
            if project.manager and project.manager != request.user and project.manager not in module_member_users:
                module_member_users.append(project.manager)
                
            for member_user in module_member_users:
                create_notification(
                    member_user, request.user, 'project_update',
                    f'New post in module: {module.name}',
                    f'{request.user.display_name} posted in the forum of module "{module.name}".',
                    project=project
                )
                
            messages.success(request, 'Forum post added.')
            return redirect('tasks:module_detail', pk=module.pk)
    return render(request, 'tasks/module_detail.html', {'module': module, 'project': project, 'members': members, 'tasks': tasks, 'files': files, 'kbs': kbs, 'forum_posts': forum_posts, 'forum_form': forum_form})

@login_required
@manager_or_admin_required
def module_edit(request, pk):
    module = get_object_or_404(ProjectModule, pk=pk)
    form = ProjectModuleForm(request.POST or None, instance=module)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Module "{module.name}" updated.')
        return redirect('tasks:module_detail', pk=module.pk)
    return render(request, 'tasks/module_form.html', {'form': form, 'project': module.project, 'title': 'Edit Module', 'module': module})

@login_required
@manager_or_admin_required
def module_delete(request, pk):
    module = get_object_or_404(ProjectModule, pk=pk)
    project = module.project
    if request.method == 'POST':
        module.delete()
        messages.success(request, 'Module deleted.')
        return redirect('tasks:module_list', pk=project.pk)
    return render(request, 'tasks/confirm_delete.html', {'object': module, 'title': 'Delete Module', 'cancel_url': reverse('tasks:module_detail', args=[module.pk])})

@login_required
@manager_or_admin_required
def module_members(request, pk):
    module = get_object_or_404(ProjectModule, pk=pk)
    project = module.project
    all_users = User.objects.filter(is_active=True).order_by('first_name', 'username')
    current_members = module.members.all()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        role = request.POST.get('role', 'developer')
        if action and user_id:
            target = get_object_or_404(User, pk=user_id)
            if action == 'add':
                ModuleMember.objects.get_or_create(module=module, user=target, defaults={'role': role})
                if not project.members.filter(pk=target.pk).exists() and project.manager != target:
                     project.members.add(target)
                create_notification(
                    target, request.user, 'project_update',
                    f'Added to module: {module.name}',
                    f'{request.user.display_name} added you to the module "{module.name}" in project "{project.name}".',
                    project=project
                )
                messages.success(request, f'{target.display_name} added to the module.')
            elif action == 'remove':
                ModuleMember.objects.filter(module=module, user=target).delete()
                messages.success(request, f'{target.display_name} removed from the module.')
        return redirect('tasks:module_members', pk=pk)
    
    return render(request, 'tasks/module_members.html', {'module': module, 'project': project, 'all_users': all_users, 'current_members': current_members})

# ─── RELEASES ─────────────────────────────────────────────────────────────────

@login_required
def release_list(request, pk):
    project = get_object_or_404(Project, pk=pk)
    # Check basic access
    is_member = project.members.filter(pk=request.user.pk).exists() or project.manager == request.user or request.user.is_admin
    is_module_member = ModuleMember.objects.filter(module__project=project, user=request.user).exists()
    
    if not is_member and not is_module_member and not request.user.role == 'student':
        messages.error(request, 'You do not have access to this project.')
        return redirect('tasks:project_list')
        
    releases = project.releases.all()
    # End users (e.g. students or non-members who just view phase releases) see only Phase releases
    is_end_user = not (is_member or is_module_member) or request.user.role == 'student'
    if is_end_user:
        releases = releases.filter(release_type='phase')
        
    return render(request, 'tasks/release_list.html', {'project': project, 'releases': releases, 'is_end_user': is_end_user})

@login_required
@manager_or_admin_required
def release_create(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = ReleaseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        release = form.save(commit=False)
        release.project = project
        release.author = request.user
        release.save()
        messages.success(request, f'Release "{release.name}" created.')
        return redirect('tasks:release_list', pk=project.pk)
    return render(request, 'tasks/release_form.html', {'form': form, 'project': project, 'title': 'Create Release'})

@login_required
def release_detail(request, pk):
    release = get_object_or_404(Release, pk=pk)
    project = release.project
    
    # Check access
    is_member = project.members.filter(pk=request.user.pk).exists() or project.manager == request.user or request.user.is_admin
    is_module_member = ModuleMember.objects.filter(module__project=project, user=request.user).exists()
    is_end_user = not (is_member or is_module_member) or request.user.role == 'student'

    if is_end_user and release.release_type != 'phase':
         messages.error(request, 'You only have access to phase releases.')
         return redirect('tasks:release_list', pk=project.pk)
         
    tasks = release.tasks.all()
    module_versions = release.module_versions.all()
    
    if request.method == 'POST' and (request.user.is_admin or request.user == project.manager or request.user == release.author):
        new_status = request.POST.get('status')
        if new_status and new_status in dict(Release.STATUS_CHOICES):
            release.status = new_status
            release.save()
            messages.success(request, f'Release status updated to {release.get_status_display()}.')
            return redirect('tasks:release_detail', pk=pk)
            
        if 'file' in request.FILES:
            from files.models import ProjectFile
            import os
            for uploaded_file in request.FILES.getlist('file'):
                new_f = ProjectFile(
                    file=uploaded_file,
                    original_name=uploaded_file.name,
                    file_size=uploaded_file.size,
                    project=project,
                    release=release,
                    uploaded_by=request.user,
                    is_public=False
                )
                ext = os.path.splitext(uploaded_file.name)[1].lower()
                new_f.extension = ext
                
                file_type = 'other'
                if ext in ProjectFile.IMAGE_EXTS: file_type = 'image'
                elif ext in ProjectFile.PDF_EXTS: file_type = 'pdf'
                elif ext in ProjectFile.DOC_EXTS: file_type = 'document'
                elif ext in ProjectFile.SHEET_EXTS: file_type = 'spreadsheet'
                elif ext in ProjectFile.CODE_EXTS: file_type = 'code'
                elif ext in ProjectFile.ARCHIVE_EXTS: file_type = 'archive'
                elif ext in ProjectFile.CAD_EXTS: file_type = 'cad'
                new_f.file_type = file_type
                new_f.save()
            messages.success(request, f"File(s) attached to release successfully.")
            return redirect('tasks:release_detail', pk=pk)

    kanban = {
        'todo':        tasks.filter(status='todo'),
        'in_progress': tasks.filter(status='in_progress'),
        'review':      tasks.filter(status='review'),
        'done':        tasks.filter(status='done'),
        'blocked':     tasks.filter(status='blocked'),
    }

    return render(request, 'tasks/release_detail.html', {'release': release, 'project': project, 'kanban': kanban, 'tasks': tasks, 'module_versions': module_versions})

@login_required
@manager_or_admin_required
def release_edit(request, pk):
    release = get_object_or_404(Release, pk=pk)
    form = ReleaseForm(request.POST or None, instance=release)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Release "{release.name}" updated.')
        return redirect('tasks:release_detail', pk=release.pk)
    return render(request, 'tasks/release_form.html', {'form': form, 'project': release.project, 'title': 'Edit Release', 'release': release})

@login_required
@manager_or_admin_required
def release_delete(request, pk):
    release = get_object_or_404(Release, pk=pk)
    project = release.project
    if request.method == 'POST':
        release.delete()
        messages.success(request, 'Release deleted.')
        return redirect('tasks:release_list', pk=project.pk)
    return render(request, 'tasks/confirm_delete.html', {'object': release, 'title': 'Delete Release', 'cancel_url': reverse('tasks:release_detail', args=[release.pk])})

@login_required
def release_download(request, pk):
    import io
    import zipfile
    from django.http import HttpResponse
    release = get_object_or_404(Release, pk=pk)
    project = release.project
    
    is_member = project.members.filter(pk=request.user.pk).exists() or project.manager == request.user or request.user.is_admin
    is_module_member = ModuleMember.objects.filter(module__project=project, user=request.user).exists()
    is_end_user = not (is_member or is_module_member) or request.user.role == 'student'

    if is_end_user and release.release_type != 'phase':
         messages.error(request, 'You only have access to phase releases.')
         return redirect('tasks:release_list', pk=project.pk)
         
    zip_buffer = io.BytesIO()
    import os
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        files_added = 0
        for mv in release.module_versions.all():
            if mv.file and mv.file.file:
                 file_path = mv.file.file.path
                 if os.path.exists(file_path):
                      zip_file.write(file_path, arcname=f"{mv.module.name}/{mv.file.original_name}")
                      files_added += 1
                      
        for f in release.direct_files.all():
            if f.file:
                file_path = f.file.path
                if os.path.exists(file_path):
                    zip_file.write(file_path, arcname=f"Direct_Files/{f.original_name}")
                    files_added += 1
                    
        if files_added == 0:
            zip_file.writestr("README.txt", "No files were attached to this release.")
    
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename={project.name}_{release.name}.zip'
    return response
