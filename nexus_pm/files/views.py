import os
import mimetypes
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count
from django.views.decorators.http import require_POST
from .models import ProjectFile, FileCategory, FileComment
from .forms import FileUploadForm, MultiFileUploadForm, FileCategoryForm, FileEditForm, FileCommentForm
from tasks.decorators import admin_required
from tasks.models import Project, Task


# ─── FILE LIST ────────────────────────────────────────────────────────────────

@login_required
def file_list(request):
    user = request.user
    search      = request.GET.get('q', '')
    type_filter = request.GET.get('type', '')
    proj_filter = request.GET.get('project', '')

    if user.is_admin:
        files = ProjectFile.objects.all()
        projects = Project.objects.all()
    else:
        accessible_projects = Project.objects.filter(
            Q(manager=user) | Q(members=user)
        ).distinct()
        files = ProjectFile.objects.filter(
            Q(project__in=accessible_projects) | Q(uploaded_by=user)
        ).distinct()
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

    return render(request, 'files/file_list.html', {
        'files':           files.select_related('project', 'task', 'uploaded_by').order_by('-created_at'),
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
    project_id = request.GET.get('project')
    task_id    = request.GET.get('task')
    project    = get_object_or_404(Project, pk=project_id) if project_id else None
    task       = get_object_or_404(Task,    pk=task_id)    if task_id    else None

    form = FileUploadForm(
        request.POST or None,
        request.FILES or None,
        user=request.user, project=project, task=task
    )

    if request.method == 'POST':
        # Handle multi-file AJAX upload
        if request.FILES.getlist('files'):
            uploaded = []
            for f in request.FILES.getlist('files'):
                pf = ProjectFile(
                    file          = f,
                    original_name = f.name,
                    project       = project,
                    task          = task,
                    uploaded_by   = request.user,
                    description   = request.POST.get('description', ''),
                    is_public     = request.POST.get('is_public') == 'on',
                )
                pf.save()
                uploaded.append({
                    'id':   pf.pk,
                    'name': pf.display_name,
                    'size': pf.file_size_display,
                    'type': pf.file_type,
                    'icon': pf.icon_class,
                })
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'files': uploaded})
            messages.success(request, f'{len(uploaded)} file(s) uploaded successfully.')
            if project:
                return redirect('files:project_files', pk=project.pk)
            return redirect('files:file_list')

        # Single file form submit
        if form.is_valid():
            pf = form.save(commit=False)
            pf.uploaded_by = request.user
            pf.original_name = request.FILES['file'].name
            # Handle versioning
            if pf.parent_file:
                pf.version = pf.parent_file.version + 1
            pf.save()
            messages.success(request, f'"{pf.display_name}" uploaded successfully.')
            return redirect('files:file_detail', pk=pf.pk)
        else:
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
    if not user.is_admin:
        if pf.project:
            has_access = (
                pf.project.members.filter(pk=user.pk).exists() or
                pf.project.manager == user or
                pf.uploaded_by == user
            )
            if not has_access:
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

    if not user.is_admin:
        if pf.project:
            has_access = (
                pf.is_public and pf.project.members.filter(pk=user.pk).exists() or
                pf.project.manager == user or
                pf.uploaded_by == user
            )
            if not has_access:
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

    if not user.is_admin:
        if pf.project:
            has_access = (
                pf.project.members.filter(pk=user.pk).exists() or
                pf.project.manager == user or
                pf.uploaded_by == user
            )
            if not has_access:
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
    if pf.uploaded_by != request.user and not request.user.is_admin:
        messages.error(request, 'You can only edit files you uploaded.')
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
    if pf.uploaded_by != request.user and not request.user.is_admin:
        messages.error(request, 'You can only delete files you uploaded.')
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

    # Access check
    if not user.is_admin:
        if not (project.members.filter(pk=user.pk).exists() or project.manager == user):
            messages.error(request, 'No access.')
            return redirect('files:file_list')

    files = project.files.all().select_related('uploaded_by', 'task', 'category')
    if type_filter: files = files.filter(file_type=type_filter)
    if cat_filter:  files = files.filter(category_id=cat_filter)
    if search:      files = files.filter(Q(original_name__icontains=search) | Q(title__icontains=search))

    categories = project.file_categories.all()
    stats = {
        'total':      files.count(),
        'total_size': files.aggregate(s=Sum('file_size'))['s'] or 0,
        'by_type':    {ft: files.filter(file_type=ft).count() for ft, _ in ProjectFile.FILE_TYPE_CHOICES},
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
