import os
import mimetypes
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count
from django.views.decorators.http import require_POST
from .models import ProjectFile, FileCategory, FileComment, DocumentAccessRight
from .forms import FileUploadForm, MultiFileUploadForm, FileCategoryForm, FileEditForm, FileCommentForm
from tasks.decorators import admin_required
from tasks.models import Project, Task, ModuleMember

def check_file_access(pf, user, access_type='view'):
    if pf.uploaded_by == user:
        return True
    if pf.project and pf.project.manager == user:
        return True
        
    explicit = DocumentAccessRight.objects.filter(file=pf, user=user).first()
    if explicit:
        if access_type == 'view': return explicit.can_view
        if access_type == 'edit': return explicit.can_edit
        if access_type == 'delete': return explicit.can_delete
        
    if access_type != 'view':
        return False
        
    module = pf.module or (pf.task.module if pf.task else None)
    if module:
         return ModuleMember.objects.filter(module=module, user=user).exists()
    elif pf.project:
         return pf.project.members.filter(pk=user.pk).exists()
    return False


# ─── FILE LIST ────────────────────────────────────────────────────────────────

@login_required
def file_list(request):
    user = request.user
    search      = request.GET.get('q', '')
    type_filter = request.GET.get('type', '')
    proj_filter = request.GET.get('project', '')
    module_filter = request.GET.get('module', '')

    accessible_projects = Project.objects.filter(
        Q(manager=user) | Q(members=user)
    ).distinct()
    
    q_filter = (
        Q(uploaded_by=user) |
        Q(project__manager=user) |
        Q(project__members=user, module__isnull=True, task__module__isnull=True) |
        Q(module__members__user=user) |
        Q(task__module__members__user=user)
    )
    
    files = ProjectFile.objects.filter(q_filter).distinct()
    projects = accessible_projects

    if search:
        files = files.filter(
            Q(original_name__icontains=search) |
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )
    if type_filter:
        files = files.filter(file_type=type_filter)
    if proj_filter:
        files = files.filter(project_id=proj_filter)
    if module_filter:
        files = files.filter(module_id=module_filter)

    # Stats
    stats = {
        'total':      files.count(),
        'total_size': files.aggregate(s=Sum('file_size'))['s'] or 0,
        'images':     files.filter(file_type='image').count(),
        'documents':  files.filter(file_type__in=['document','pdf']).count(),
        'code':       files.filter(file_type='code').count(),
        'archives':   files.filter(file_type='archive').count(),
    }

    def fmt_size(s):
        if s < 1024**2: return f"{s/1024:.1f} KB"
        if s < 1024**3: return f"{s/1024**2:.1f} MB"
        return f"{s/1024**3:.2f} GB"

    stats['total_size_display'] = fmt_size(stats['total_size'])

    from django.core.paginator import Paginator
    
    files_ordered = files.select_related('project', 'task', 'uploaded_by').order_by('-created_at')
    paginator = Paginator(files_ordered, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'files/file_list.html', {
        'files':           page_obj,
        'page_obj':        page_obj,
        'projects':        projects,
        'stats':           stats,
        'type_choices':    ProjectFile.FILE_TYPE_CHOICES,
        'search':          search,
        'type_filter':     type_filter,
        'proj_filter':     proj_filter,
    })


# ─── UPLOAD ───────────────────────────────────────────────────────────────────

@login_required
def file_upload(request):
    # Resolve project/task from GET (pre-linked) OR POST (form selection)
    if request.method == 'POST':
        project_id = request.POST.get('project') or request.GET.get('project')
        task_id    = request.POST.get('task')    or request.GET.get('task')
    else:
        project_id = request.GET.get('project')
        task_id    = request.GET.get('task')

    parent_id = request.GET.get('parent_id')

    project = None
    task    = None
    parent  = None
    if project_id:
        try:
            project = Project.objects.get(pk=project_id)
        except (Project.DoesNotExist, ValueError):
            project = None
    if task_id:
        try:
            task = Task.objects.get(pk=task_id)
        except (Task.DoesNotExist, ValueError):
            task = None
    if parent_id:
        try:
            parent = ProjectFile.objects.get(pk=parent_id)
        except (ProjectFile.DoesNotExist, ValueError):
            parent = None

    form = FileUploadForm(
        request.POST or None,
        request.FILES or None,
        user=request.user, project=project, task=task, initial={'parent_file': parent}
    )

    if request.method == 'POST':
        # ── Multi-file upload (name="files" multiple input) ──────────────────
        uploaded_files = request.FILES.getlist('files')
        if uploaded_files:
            uploaded = []
            description = request.POST.get('description', '')
            is_public   = request.POST.get('is_public') == 'on'

            for f in uploaded_files:
                pf = ProjectFile(
                    file          = f,
                    original_name = f.name,
                    project       = project,
                    task          = task,
                    uploaded_by   = request.user,
                    description   = description,
                    is_public     = is_public,
                )
                pf.save()
                uploaded.append({
                    'id':   pf.pk,
                    'name': pf.display_name,
                    'size': pf.file_size_display,
                    'type': pf.file_type,
                    'icon': pf.icon_class,
                    'url':  f'/files/{pf.pk}/',
                })

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'files': uploaded})

            messages.success(request, f'{len(uploaded)} file(s) uploaded successfully.')
            if project:
                return redirect('files:project_files', pk=project.pk)
            return redirect('files:file_list')

        # ── Single-file form fallback ─────────────────────────────────────────
        if 'file' in request.FILES and form.is_valid():
            pf = form.save(commit=False)
            pf.uploaded_by   = request.user
            pf.original_name = request.FILES['file'].name
            if pf.parent_file:
                pf.version = pf.parent_file.version + 1
            pf.save()
            messages.success(request, f'"{pf.display_name}" uploaded successfully.')
            return redirect('files:file_detail', pk=pf.pk)

        if not uploaded_files and 'file' not in request.FILES:
            messages.error(request, 'Please select at least one file to upload.')
        elif not form.is_valid() and 'file' in request.FILES:
            messages.error(request, 'Please fix the errors below.')

    return render(request, 'files/file_upload.html', {
        'form':    form,
        'project': project,
        'task':    task,
    })


# ─── FILE DETAIL ──────────────────────────────────────────────────────────────

@login_required
def file_detail(request, pk):
    pf   = get_object_or_404(ProjectFile, pk=pk)
    user = request.user

    # Access control
    if not check_file_access(pf, user, 'view'):
        messages.error(request, 'You do not have access to this file.')
        return redirect('files:file_list')

    comments     = pf.comments.select_related('author').all()
    versions     = pf.versions.all() if not pf.parent_file else []
    comment_form = FileCommentForm()

    # Handle comment POST
    if request.method == 'POST':
        comment_form = FileCommentForm(request.POST)
        if comment_form.is_valid():
            c = comment_form.save(commit=False)
            c.file   = pf
            c.author = user
            c.save()
            messages.success(request, 'Comment added.')
            return redirect('files:file_detail', pk=pk)

    # Text file preview content
    text_content = None
    if pf.is_text_viewable and pf.file_size < 500_000:
        try:
            with pf.file.open('r') as f:
                text_content = f.read()
        except Exception:
            text_content = None

    return render(request, 'files/file_detail.html', {
        'file':         pf,
        'comments':     comments,
        'versions':     versions,
        'comment_form': comment_form,
        'text_content': text_content,
    })


# ─── DOWNLOAD ─────────────────────────────────────────────────────────────────

@login_required
def file_download(request, pk):
    pf   = get_object_or_404(ProjectFile, pk=pk)
    user = request.user

    if not check_file_access(pf, user, 'view'):
        raise Http404

    # Increment download counter
    ProjectFile.objects.filter(pk=pk).update(download_count=pf.download_count + 1)

    try:
        response = FileResponse(
            pf.file.open('rb'),
            as_attachment=True,
            filename=pf.original_name
        )
        return response
    except FileNotFoundError:
        raise Http404("File not found on server.")


# ─── INLINE VIEW (preview in browser) ────────────────────────────────────────

@login_required
def file_view(request, pk):
    """Serve file inline (for images/PDF/text preview in browser)."""
    pf = get_object_or_404(ProjectFile, pk=pk)
    user = request.user

    if not check_file_access(pf, user, 'view'):
        raise Http404

    try:
        mime, _ = mimetypes.guess_type(pf.original_name)
        response = FileResponse(pf.file.open('rb'), content_type=mime or 'application/octet-stream')
        response['Content-Disposition'] = f'inline; filename="{pf.original_name}"'
        return response
    except FileNotFoundError:
        raise Http404("File not found on server.")


# ─── EDIT / DELETE ────────────────────────────────────────────────────────────

@login_required
def file_edit(request, pk):
    pf = get_object_or_404(ProjectFile, pk=pk)
    if not check_file_access(pf, request.user, 'edit'):
        messages.error(request, 'You do not have permission to edit this file.')
        return redirect('files:file_detail', pk=pk)

    form = FileEditForm(request.POST or None, instance=pf)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'"{pf.display_name}" updated.')
        return redirect('files:file_detail', pk=pk)

    return render(request, 'files/file_edit.html', {'form': form, 'file': pf})


@login_required
def file_delete(request, pk):
    pf = get_object_or_404(ProjectFile, pk=pk)
    if not check_file_access(pf, request.user, 'delete'):
        messages.error(request, 'You do not have permission to delete this file.')
        return redirect('files:file_detail', pk=pk)

    project = pf.project
    if request.method == 'POST':
        name = pf.display_name
        try:
            pf.file.delete(save=False)   # delete from disk
        except Exception:
            pass
        pf.delete()
        messages.success(request, f'"{name}" deleted permanently.')
        if project:
            return redirect('files:project_files', pk=project.pk)
        return redirect('files:file_list')

    return render(request, 'files/file_confirm_delete.html', {'file': pf})


# ─── PROJECT FILE BROWSER ─────────────────────────────────────────────────────

@login_required
def project_files(request, pk):
    project     = get_object_or_404(Project, pk=pk)
    user        = request.user
    type_filter = request.GET.get('type', '')
    cat_filter  = request.GET.get('category', '')
    search      = request.GET.get('q', '')

    # Access check (Removed admin override per requirements)
    is_project_member = project.members.filter(pk=user.pk).exists() or project.manager == user
    is_module_member = ModuleMember.objects.filter(module__project=project, user=user).exists()
    
    if not (is_project_member or is_module_member):
        messages.error(request, 'No access to project files.')
        return redirect('files:file_list')

    # Filter files for visibility
    q_filter = (
        Q(uploaded_by=user) |
        Q(project__manager=user) |
        Q(project__members=user, module__isnull=True, task__module__isnull=True) |
        Q(module__members__user=user) |
        Q(task__module__members__user=user)
    )
    
    files = project.files.filter(q_filter).select_related('uploaded_by', 'task', 'category').distinct()
    if type_filter: files = files.filter(file_type=type_filter)
    if cat_filter:  files = files.filter(category_id=cat_filter)
    if search:      files = files.filter(Q(original_name__icontains=search) | Q(title__icontains=search))

    categories = project.file_categories.all()
    stats = {
        'total':      files.count(),
        'total_size': files.aggregate(s=Sum('file_size'))['s'] or 0,
        'by_type':    [{'key': ft, 'label': label, 'count': files.filter(file_type=ft).count()} for ft, label in ProjectFile.FILE_TYPE_CHOICES],
    }

    return render(request, 'files/project_files.html', {
        'project':     project,
        'files':       files.order_by('-created_at'),
        'categories':  categories,
        'stats':       stats,
        'type_choices': ProjectFile.FILE_TYPE_CHOICES,
        'type_filter': type_filter,
        'cat_filter':  cat_filter,
        'search':      search,
    })

# ─── FILE ACCESS MANAGEMENT ───────────────────────────────────────────────────

@login_required
def file_access(request, pk):
    pf = get_object_or_404(ProjectFile, pk=pk)
    if not (request.user.is_admin or (pf.project and pf.project.manager == request.user)):
        messages.error(request, 'Only managers and admins can manage access rights.')
        return redirect('files:file_detail', pk=pk)
        
    access_rights = DocumentAccessRight.objects.filter(file=pf)
    from accounts.models import User
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
                ar, created = DocumentAccessRight.objects.get_or_create(file=pf, user=target_user)
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
        return redirect('files:file_access', pk=pk)
        
    return render(request, 'files/file_access.html', {'file': pf, 'access_rights': access_rights, 'all_users': all_users})
