from django import forms
from .models import Project, Task, Comment, BugReport, CalendarEvent, KnowledgeBaseNote
from accounts.models import User


class ProjectForm(forms.ModelForm):
    budget = forms.DecimalField(max_digits=12, decimal_places=2, required=False, min_value=0,
                                widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 50000.00', 'step': '0.01'}))

    class Meta:
        model  = Project
        fields = ['name', 'description', 'module', 'status', 'priority',
                  'start_date', 'end_date', 'manager', 'members']
        widgets = {
            'name':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Project name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe the project...'}),
            'module':      forms.Select(attrs={'class': 'form-control'}),
            'status':      forms.Select(attrs={'class': 'form-control'}),
            'priority':    forms.Select(attrs={'class': 'form-control'}),
            'start_date':  forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date':    forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'manager':     forms.Select(attrs={'class': 'form-control'}),
            'members':     forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            try:
                self.fields['budget'].initial = self.instance.budget.total_amount
            except Exception:
                pass

        self.fields['manager'].queryset    = User.objects.filter(is_active=True, role__in=['admin', 'project_manager'])
        self.fields['members'].queryset    = User.objects.filter(is_active=True).order_by('team', 'first_name')
        self.fields['manager'].empty_label = '— Select Project Manager —'
        self.fields['manager'].required    = False
        self.fields['members'].required    = False

        if user and user.is_admin:
            for field in ['module', 'status', 'priority', 'start_date', 'end_date', 'members']:
                if field in self.fields:
                    del self.fields[field]


class TaskForm(forms.ModelForm):
    class Meta:
        model  = Task
        fields = ['title', 'description', 'project', 'module', 'task_type', 'status',
                  'priority', 'assignees', 'parent_task', 'due_date',
                  'estimated_hours', 'tags']
        widgets = {
            'title':           forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'What needs to be done?'}),
            'description':     forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Details, acceptance criteria...'}),
            'project':         forms.Select(attrs={'class': 'form-control', 'id': 'id_task_project'}),
            'module':          forms.Select(attrs={'class': 'form-control', 'id': 'id_task_module'}),
            'task_type':       forms.Select(attrs={'class': 'form-control'}),
            'status':          forms.Select(attrs={'class': 'form-control'}),
            'priority':        forms.Select(attrs={'class': 'form-control'}),
            'assignees':       forms.SelectMultiple(attrs={'class': 'form-control'}),
            'parent_task':     forms.Select(attrs={'class': 'form-control'}),
            'due_date':        forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'estimated_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'placeholder': '0.0'}),
            'tags':            forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'tag1, tag2, tag3'}),
        }

    def __init__(self, *args, user=None, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active members in assigned_to
        if project:
            # Members of the project + manager
            member_ids = list(project.members.values_list('pk', flat=True))
            if project.manager:
                member_ids.append(project.manager.pk)
            self.fields['assignees'].queryset = User.objects.filter(
                pk__in=member_ids, is_active=True
            ).order_by('first_name', 'username')
            self.fields['parent_task'].queryset = Task.objects.filter(
                project=project, parent_task__isnull=True
            )
            from .models import ProjectModule
            self.fields['module'].queryset = ProjectModule.objects.filter(project=project)
            # Pre-select project
            self.fields['project'].initial = project
        else:
            self.fields['assignees'].queryset = User.objects.filter(is_active=True).order_by('first_name')
            self.fields['parent_task'].queryset = Task.objects.filter(parent_task__isnull=True)
            from .models import ProjectModule
            self.fields['module'].queryset = ProjectModule.objects.none()

        self.fields['assignees'].required = False
        self.fields['parent_task'].empty_label = '— No parent task —'
        self.fields['module'].empty_label = '— No module selected —'


class CommentForm(forms.ModelForm):
    class Meta:
        model  = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Write a comment...',
            })
        }


class BugReportForm(forms.ModelForm):
    class Meta:
        model  = BugReport
        fields = ['title', 'project', 'severity', 'description',
                  'steps_to_reproduce', 'expected_behavior', 'actual_behavior',
                  'assignees', 'linked_task', 'status']
        widgets = {
            'title':               forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Short descriptive title'}),
            'project':             forms.Select(attrs={'class': 'form-control', 'id': 'id_bug_project'}),
            'severity':            forms.Select(attrs={'class': 'form-control'}),
            'status':              forms.Select(attrs={'class': 'form-control'}),
            'description':         forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'What went wrong?'}),
            'steps_to_reproduce':  forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '1. Go to...\n2. Click on...\n3. See error'}),
            'expected_behavior':   forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'What should happen?'}),
            'actual_behavior':     forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'What actually happened?'}),
            'assignees':           forms.SelectMultiple(attrs={'class': 'form-control'}),
            'linked_task':         forms.Select(attrs={'class': 'form-control', 'id': 'id_linked_task'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        from django.db.models import Q

        # assignees: project members if project is known (edit mode), else all active users
        if self.instance and self.instance.pk and self.instance.project_id:
            proj = self.instance.project
            member_ids = list(proj.members.values_list('pk', flat=True))
            if proj.manager_id:
                member_ids.append(proj.manager_id)
            self.fields['assignees'].queryset = User.objects.filter(
                pk__in=member_ids, is_active=True
            ).order_by('first_name', 'username')
        else:
            self.fields['assignees'].queryset = User.objects.filter(is_active=True).order_by('first_name')

        self.fields['assignees'].required = False
        self.fields['linked_task'].empty_label = '— None —'
        self.fields['status'].required = False
        self.fields['project'].required = False
        
        if getattr(self, 'instance', None) and self.instance.pk and user:
            # We bypass the single assignee check here or we check if user in assignees
            is_assignee = self.instance.assignees.filter(pk=user.pk).exists() if getattr(self.instance, 'pk', None) else False
            if is_assignee and user != self.instance.reported_by and getattr(user, 'is_admin', False) == False:
                for field_name, field in self.fields.items():
                    if field_name != 'status':
                        field.disabled = True

        if user and not user.is_admin:
            accessible = Project.objects.filter(Q(manager=user) | Q(members=user)).distinct()
            self.fields['project'].queryset = accessible
            if self.instance and self.instance.pk and self.instance.project_id:
                self.fields['linked_task'].queryset = Task.objects.filter(
                    project=self.instance.project
                ).order_by('title')
            else:
                self.fields['linked_task'].queryset = Task.objects.filter(
                    project__in=accessible
                ).order_by('title')
        else:
            if self.instance and self.instance.pk and self.instance.project_id:
                self.fields['linked_task'].queryset = Task.objects.filter(
                    project=self.instance.project
                ).order_by('title')
            else:
                self.fields['linked_task'].queryset = Task.objects.all().order_by('title')

    def clean(self):
        cleaned_data = super().clean()
        project = cleaned_data.get('project')
        assignees = cleaned_data.get('assignees')
        
        if project and assignees:
            member_ids = list(project.members.values_list('pk', flat=True))
            if project.manager_id:
                member_ids.append(project.manager_id)
            for assignee in assignees:
                if assignee.pk not in member_ids:
                    self.add_error('assignees', f'The assigned user ({assignee.display_name}) must be a member or manager of the selected project.')
                
        return cleaned_data


class CalendarEventForm(forms.ModelForm):
    class Meta:
        model  = CalendarEvent
        fields = ['title', 'description', 'event_type', 'project', 'task',
                  'start_datetime', 'end_datetime', 'attendees', 'color']
        widgets = {
            'title':          forms.TextInput(attrs={'class': 'form-control'}),
            'description':    forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'event_type':     forms.Select(attrs={'class': 'form-control'}),
            'project':        forms.Select(attrs={'class': 'form-control'}),
            'task':           forms.Select(attrs={'class': 'form-control'}),
            'start_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_datetime':   forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'attendees':      forms.CheckboxSelectMultiple(),
            'color':          forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].empty_label  = '— No project —'
        self.fields['project'].required     = False
        self.fields['task'].empty_label     = '— No task —'
        self.fields['task'].required        = False
        self.fields['attendees'].queryset   = User.objects.filter(is_active=True).order_by('first_name')
        self.fields['attendees'].required   = False


class KnowledgeBaseNoteForm(forms.ModelForm):
    class Meta:
        model = KnowledgeBaseNote
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Note title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 15, 'placeholder': '# Heading\n\nWrite your note in Markdown...'}),
            'module': forms.Select(attrs={'class': 'form-control'}),
        }

class ProjectModuleForm(forms.ModelForm):
    class Meta:
        from .models import ProjectModule
        model = ProjectModule
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Module Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ReleaseForm(forms.ModelForm):
    class Meta:
        from .models import Release
        model = Release
        fields = ['name', 'release_type', 'status', 'target_date', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. May 2025 Release'}),
            'release_type': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'target_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ModuleForumPostForm(forms.ModelForm):
    class Meta:
        from .models import ModuleForumPost
        model = ModuleForumPost
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Discuss this module...',
            })
        }
