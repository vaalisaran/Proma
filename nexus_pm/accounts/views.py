from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from .models import User
from .forms import LoginForm, UserCreateForm, UserEditForm, AdminPasswordResetForm, UserSelfPasswordChangeForm
from tasks.decorators import admin_required


# ─── AUTH ────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('tasks:dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            if not user.is_active:
                messages.error(request, 'Your account has been deactivated. Contact the administrator.')
                return render(request, 'accounts/login.html', {'form': form})
            login(request, user)
            messages.success(request, f'Welcome back, {user.display_name}!')
            return redirect(request.GET.get('next', 'tasks:dashboard'))
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    name = request.user.display_name
    logout(request)
    messages.info(request, f'Goodbye, {name}! You have been logged out.')
    return redirect('accounts:login')


# ─── USER MANAGEMENT (Admin Only) ────────────────────────────────────────────

@login_required
@admin_required
def user_list(request):
    search = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')
    team_filter = request.GET.get('team', '')
    status_filter = request.GET.get('status', '')

    users = User.objects.all().order_by('-date_joined')

    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(designation__icontains=search)
        )
    if role_filter:
        users = users.filter(role=role_filter)
    if team_filter:
        users = users.filter(team=team_filter)
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)

    # Stats
    stats = {
        'total': User.objects.count(),
        'active': User.objects.filter(is_active=True).count(),
        'inactive': User.objects.filter(is_active=False).count(),
        'admins': User.objects.filter(role='admin').count(),
        'managers': User.objects.filter(role='project_manager').count(),
        'members': User.objects.filter(role='member').count(),
    }

    from django.core.paginator import Paginator
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'accounts/user_list.html', {
        'users': page_obj,
        'page_obj': page_obj,
        'stats': stats,
        'search': search,
        'role_filter': role_filter,
        'team_filter': team_filter,
        'status_filter': status_filter,
        'role_choices': User.ROLE_CHOICES,
        'team_choices': User.MODULE_CHOICES,
    })


@login_required
@admin_required
def user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            messages.success(request, f'✅ User "{user.username}" created. They can now login with the credentials you set.')
            return redirect('accounts:user_detail', pk=user.pk)
        else:
            messages.error(request, 'Please fix the errors below.')
    return render(request, 'accounts/user_form.html', {
        'form': form, 'title': 'Create New User', 'action': 'Create User'
    })


@login_required
@admin_required
def user_detail(request, pk):
    """Admin view of a specific user — shows their projects, tasks, credentials info."""
    from tasks.models import Project, Task
    profile_user = get_object_or_404(User, pk=pk)

    assigned_tasks = Task.objects.filter(assigned_to=profile_user).select_related('project')
    managed_projects = Project.objects.filter(manager=profile_user)
    member_projects = Project.objects.filter(members=profile_user)

    task_stats = {
        'total': assigned_tasks.count(),
        'todo': assigned_tasks.filter(status='todo').count(),
        'in_progress': assigned_tasks.filter(status='in_progress').count(),
        'done': assigned_tasks.filter(status='done').count(),
        'overdue': sum(1 for t in assigned_tasks if t.is_overdue),
    }

    return render(request, 'accounts/user_detail.html', {
        'profile_user': profile_user,
        'assigned_tasks': assigned_tasks[:10],
        'managed_projects': managed_projects,
        'member_projects': member_projects,
        'task_stats': task_stats,
    })


@login_required
@admin_required
def user_edit(request, pk):
    edit_user = get_object_or_404(User, pk=pk)
    form = UserEditForm(request.POST or None, instance=edit_user)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, f'User "{edit_user.username}" updated successfully.')
            return redirect('accounts:user_detail', pk=edit_user.pk)
        else:
            messages.error(request, 'Please fix the errors below.')
    return render(request, 'accounts/user_form.html', {
        'form': form, 'title': f'Edit User — {edit_user.username}',
        'action': 'Save Changes', 'edit_user': edit_user
    })


@login_required
@admin_required
def user_reset_password(request, pk):
    """Admin resets another user's password."""
    reset_user = get_object_or_404(User, pk=pk)
    form = AdminPasswordResetForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            reset_user.set_password(form.cleaned_data['new_password1'])
            reset_user.save()
            messages.success(request, f'✅ Password for "{reset_user.username}" has been reset successfully.')
            return redirect('accounts:user_detail', pk=reset_user.pk)
        else:
            messages.error(request, 'Please fix the errors below.')
    return render(request, 'accounts/user_reset_password.html', {
        'form': form, 'reset_user': reset_user
    })


@login_required
@admin_required
def user_delete(request, pk):
    del_user = get_object_or_404(User, pk=pk)
    if del_user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('accounts:user_list')
    if request.method == 'POST':
        username = del_user.username
        del_user.delete()
        messages.success(request, f'User "{username}" permanently deleted.')
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_confirm_delete.html', {'user_obj': del_user})


@login_required
@admin_required
def user_toggle_active(request, pk):
    toggle_user = get_object_or_404(User, pk=pk)
    if toggle_user == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('accounts:user_list')
    toggle_user.is_active = not toggle_user.is_active
    toggle_user.save()
    action = 'activated' if toggle_user.is_active else 'deactivated'
    messages.success(request, f'User "{toggle_user.username}" {action}.')
    return redirect(request.META.get('HTTP_REFERER', 'accounts:user_list'))


# ─── PROFILE (Self) ───────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    from tasks.models import Task, Project
    u = request.user
    my_tasks = Task.objects.filter(assigned_to=u)
    my_projects = Project.objects.filter(Q(manager=u) | Q(members=u)).distinct()
    task_stats = {
        'total': my_tasks.count(),
        'todo': my_tasks.filter(status='todo').count(),
        'in_progress': my_tasks.filter(status='in_progress').count(),
        'done': my_tasks.filter(status='done').count(),
        'overdue': sum(1 for t in my_tasks if t.is_overdue),
    }
    return render(request, 'accounts/profile.html', {
        'profile_user': u,
        'my_tasks': my_tasks[:8],
        'my_projects': my_projects[:6],
        'task_stats': task_stats,
    })


@login_required
def change_password(request):
    """Any logged-in user can change their own password."""
    form = UserSelfPasswordChangeForm(user=request.user, data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            request.user.set_password(form.cleaned_data['new_password1'])
            request.user.save()
            # Keep session alive after password change
            update_session_auth_hash(request, request.user)
            messages.success(request, '✅ Your password has been changed successfully.')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please fix the errors below.')
    return render(request, 'accounts/change_password.html', {'form': form})

@login_required
def settings_view(request):
    from tasks.models import SystemSettings, SystemIssue
    
    # Load settings
    sys_settings = SystemSettings.get_settings()
    
    # Process actions
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_profile':
            user = request.user
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.nickname = request.POST.get('nickname', user.nickname)
            # Handle password change inline or use change_password functionality
            if request.POST.get('new_password'):
                user.set_password(request.POST.get('new_password'))
                update_session_auth_hash(request, user)
            user.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:settings')
            
        elif action == 'report_issue':
            SystemIssue.objects.create(
                title=request.POST.get('title'),
                description=request.POST.get('description'),
                issue_type=request.POST.get('issue_type', 'bug'),
                reported_by=request.user
            )
            messages.success(request, 'Thank you! Your issue has been reported and will be reviewed by Project Managers.')
            return redirect('accounts:settings')
            
        elif action == 'update_system_settings' and request.user.is_admin:
            sys_settings.primary_color = request.POST.get('primary_color', sys_settings.primary_color)
            sys_settings.font_size = request.POST.get('font_size', sys_settings.font_size)
            sys_settings.default_pm_password = request.POST.get('default_pm_password', sys_settings.default_pm_password)
            sys_settings.save()
            messages.success(request, 'System settings updated successfully.')
            return redirect('accounts:settings')
            
    # For Project Managers: load reported issues
    reported_issues = []
    if request.user.is_project_manager:
        reported_issues = SystemIssue.objects.all()

    return render(request, 'accounts/settings.html', {
        'sys_settings': sys_settings,
        'reported_issues': reported_issues
    })


# ─── Superadmin: Change User Role (AJAX) ─────────────────────────────────────

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt


@login_required
@require_POST
def change_user_role(request, pk):
    """
    Superadmin or admin can change any user's role via AJAX.
    Returns JSON so the page can show a popup notification without reload.
    """
    if not (request.user.is_superuser or request.user.is_admin):
        return JsonResponse({'ok': False, 'error': 'Permission denied.'}, status=403)

    target_user = get_object_or_404(User, pk=pk)

    # Superuser-only guard: non-superuser admins cannot elevate to superuser
    # or demote a superuser
    if target_user.is_superuser and not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Cannot change a superuser account.'}, status=403)

    if target_user == request.user:
        return JsonResponse({'ok': False, 'error': 'You cannot change your own role here.'}, status=400)

    new_role = request.POST.get('role', '')
    valid_roles = [r[0] for r in User.ROLE_CHOICES]
    if new_role not in valid_roles:
        return JsonResponse({'ok': False, 'error': f'Invalid role: {new_role}'}, status=400)

    old_role = target_user.get_role_display()
    target_user.role = new_role
    target_user.save(update_fields=['role'])

    return JsonResponse({
        'ok': True,
        'message': f'✅ {target_user.display_name} role changed from {old_role} to {target_user.get_role_display()}.',
        'new_role': new_role,
        'new_role_display': target_user.get_role_display(),
    })
