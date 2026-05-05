from django import forms

from accounts.models import User

from .models import BugReport, CalendarEvent, Comment, KnowledgeBaseNote, Project, Task


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["project_id", "name", "description", "image", "background_color", "button_color", "start_date", "managers", "members"]
        widgets = {
            "project_id": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Project ID (Auto-generated if empty)"}
            ),
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Project name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Describe the project...",
                }
            ),
            "start_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "background_color": forms.TextInput(attrs={"class": "form-control", "type": "color"}),
            "button_color": forms.TextInput(attrs={"class": "form-control", "type": "color"}),
            "managers": forms.SelectMultiple(attrs={"class": "form-control"}),
            "members": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["managers"].queryset = User.objects.filter(
            is_active=True, role__in=["admin", "project_manager"]
        )
        self.fields["members"].queryset = User.objects.filter(is_active=True).order_by(
            "team", "first_name"
        )
        self.fields["managers"].required = False
        self.fields["members"].required = False
        self.fields["project_id"].required = False

        if user and user.is_admin:
            for field in ["start_date", "members"]:
                if field in self.fields:
                    del self.fields[field]


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            "task_id",
            "title",
            "description",
            "project",
            "requirement",
            "module",
            "task_type",
            "status",
            "priority",
            "assignees",
            "deadline",
            "parent_task",
            "tags",
        ]
        widgets = {
            "task_id": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Task ID (Auto-generated if empty)"}
            ),
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "What needs to be done?"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Details, acceptance criteria...",
                }
            ),
            "project": forms.Select(
                attrs={"class": "form-control", "id": "id_task_project"}
            ),
            "requirement": forms.Select(
                attrs={"class": "form-control", "id": "id_task_requirement"}
            ),
            "module": forms.Select(
                attrs={"class": "form-control", "id": "id_task_module"}
            ),
            "task_type": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "priority": forms.Select(attrs={"class": "form-control"}),
            "assignees": forms.SelectMultiple(attrs={"class": "form-control"}),
            "deadline": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "parent_task": forms.Select(attrs={"class": "form-control"}),
            "tags": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "tag1, tag2, tag3"}
            ),
        }

    def __init__(self, *args, user=None, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import ProjectModule, Requirement
        
        # Only show active members in assigned_to
        if project:
            # Members of the project + managers
            member_ids = list(project.members.values_list("pk", flat=True))
            member_ids.extend(project.managers.values_list("pk", flat=True))
            self.fields["assignees"].queryset = User.objects.filter(
                pk__in=member_ids, is_active=True
            ).order_by("first_name", "username")
            self.fields["parent_task"].queryset = Task.objects.filter(
                project=project, parent_task__isnull=True
            )

            self.fields["module"].queryset = ProjectModule.objects.filter(
                project=project
            )
            self.fields["requirement"].queryset = Requirement.objects.filter(
                project=project
            )
            # Pre-select project
            self.fields["project"].initial = project
        
        # Handle dynamic project selection during POST to avoid "Select a valid choice" error
        if self.data and self.data.get('project'):
            try:
                p_id = self.data.get('project')
                self.fields["module"].queryset = ProjectModule.objects.filter(project_id=p_id)
                self.fields["requirement"].queryset = Requirement.objects.filter(project_id=p_id)
                self.fields["parent_task"].queryset = Task.objects.filter(project_id=p_id, parent_task__isnull=True)
            except (ValueError, TypeError):
                pass
        else:
            self.fields["assignees"].queryset = User.objects.filter(
                is_active=True
            ).order_by("first_name")
            self.fields["parent_task"].queryset = Task.objects.filter(
                parent_task__isnull=True
            )

            self.fields["module"].queryset = ProjectModule.objects.none()
            self.fields["requirement"].queryset = Requirement.objects.none()

        self.fields["assignees"].required = False
        self.fields["parent_task"].empty_label = "— No parent task —"
        self.fields["module"].empty_label = "— No module selected —"
        self.fields["requirement"].empty_label = "— No requirement (Optional) —"
        self.fields["requirement"].required = False
        self.fields["task_id"].required = False




class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content", "attachment"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Write a comment...",
                }
            ),
            "attachment": forms.FileInput(attrs={"class": "form-control"}),
        }


class BugReportForm(forms.ModelForm):
    class Meta:
        model = BugReport
        fields = [
            "title",
            "project",
            "severity",
            "description",
            "steps_to_reproduce",
            "expected_behavior",
            "actual_behavior",
            "assignees",
            "linked_task",
            "status",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Short descriptive title",
                }
            ),
            "project": forms.Select(
                attrs={"class": "form-control", "id": "id_bug_project"}
            ),
            "severity": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "What went wrong?",
                }
            ),
            "steps_to_reproduce": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "1. Go to...\n2. Click on...\n3. See error",
                }
            ),
            "expected_behavior": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "What should happen?",
                }
            ),
            "actual_behavior": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "What actually happened?",
                }
            ),
            "assignees": forms.SelectMultiple(attrs={"class": "form-control"}),
            "linked_task": forms.Select(
                attrs={"class": "form-control", "id": "id_linked_task"}
            ),
        }

    def __init__(self, *args, user=None, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        from django.db.models import Q

        # Set initial project if provided
        if project:
            self.fields["project"].initial = project

        # Determine target project for querysets
        target_project = project
        if (
            not target_project
            and self.instance
            and self.instance.pk
            and self.instance.project_id
        ):
            target_project = self.instance.project

        # assignees: project members if project is known, else all active users
        if target_project:
            member_ids = list(target_project.members.values_list("pk", flat=True))
            member_ids.extend(target_project.managers.values_list("pk", flat=True))
            self.fields["assignees"].queryset = User.objects.filter(
                pk__in=member_ids, is_active=True
            ).order_by("first_name", "username")

            self.fields["linked_task"].queryset = Task.objects.filter(
                project=target_project
            ).order_by("title")
        else:
            self.fields["assignees"].queryset = User.objects.filter(
                is_active=True
            ).order_by("first_name")

            if user and not user.is_admin:
                accessible = Project.objects.filter(
                    Q(managers=user) | Q(members=user)
                ).distinct()
                self.fields["linked_task"].queryset = Task.objects.filter(
                    project__in=accessible
                ).order_by("title")
            else:
                self.fields["linked_task"].queryset = Task.objects.all().order_by(
                    "title"
                )

        self.fields["assignees"].required = False
        self.fields["linked_task"].empty_label = "— None —"
        self.fields["status"].required = False
        self.fields["project"].required = False

        # Permissions check: disable fields if user is only an assignee (not reporter/admin)
        if self.instance and self.instance.pk and user:
            is_assignee = self.instance.assignees.filter(pk=user.pk).exists()
            if (
                is_assignee
                and user != self.instance.reported_by
                and not getattr(user, "is_admin", False)
            ):
                for field_name, field in self.fields.items():
                    if field_name != "status":
                        field.disabled = True

        # Project queryset for non-admins
        if user and not user.is_admin:
            accessible = Project.objects.filter(
                Q(managers=user) | Q(members=user)
            ).distinct()
            self.fields["project"].queryset = accessible

    def clean(self):
        cleaned_data = super().clean()
        project = cleaned_data.get("project")
        assignees = cleaned_data.get("assignees")

        if project and assignees:
            member_ids = list(project.members.values_list("pk", flat=True))
            member_ids.extend(project.managers.values_list("pk", flat=True))
            for assignee in assignees:
                if assignee.pk not in member_ids:
                    self.add_error(
                        "assignees",
                        f"The assigned user ({assignee.display_name}) must be a member or manager of the selected project.",
                    )

        return cleaned_data


class CalendarEventForm(forms.ModelForm):
    class Meta:
        model = CalendarEvent
        fields = [
            "title",
            "description",
            "event_type",
            "project",
            "task",
            "start_datetime",
            "end_datetime",
            "attendees",
            "meeting_link",
            "meeting_password",
            "color",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "event_type": forms.Select(attrs={"class": "form-control"}),
            "project": forms.Select(attrs={"class": "form-control"}),
            "task": forms.Select(attrs={"class": "form-control"}),
            "start_datetime": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "end_datetime": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "attendees": forms.CheckboxSelectMultiple(),
            "meeting_link": forms.URLInput(attrs={"class": "form-control", "placeholder": "Meeting URL (optional)"}),
            "meeting_password": forms.TextInput(attrs={"class": "form-control", "placeholder": "Meeting Password (optional)"}),
            "color": forms.TextInput(attrs={"class": "form-control", "type": "color"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].empty_label = "— No project —"
        self.fields["project"].required = False
        self.fields["task"].empty_label = "— No task —"
        self.fields["task"].required = False
        self.fields["attendees"].queryset = User.objects.filter(
            is_active=True
        ).order_by("first_name")
        self.fields["attendees"].required = False


class KnowledgeBaseNoteForm(forms.ModelForm):
    class Meta:
        model = KnowledgeBaseNote
        fields = ["title", "content"]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Note title"}
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 15,
                    "placeholder": "# Heading\n\nWrite your note in Markdown...",
                }
            ),
            "module": forms.Select(attrs={"class": "form-control"}),
        }


class ProjectModuleForm(forms.ModelForm):
    class Meta:
        from .models import ProjectModule

        model = ProjectModule
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Module Name"}
            ),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class ReleaseForm(forms.ModelForm):
    class Meta:
        from .models import Release

        model = Release
        fields = [
            "name",
            "tag_name",
            "release_type",
            "status",
            "target_date",
            "is_draft",
            "is_prerelease",
            "description",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. May 2025 Release"}
            ),
            "tag_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. v1.0.0"}
            ),
            "release_type": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "target_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "is_draft": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_prerelease": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 8,
                    "placeholder": "Write release notes in Markdown...",
                }
            ),
        }

    def __init__(self, *args, project=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        from django.db.models import Q
        from files.models import ProjectFile

        if not project and user:
            if user.is_admin:
                self.fields["project"] = forms.ModelChoiceField(
                    queryset=Project.objects.all(),
                    widget=forms.Select(attrs={"class": "form-control"}),
                    required=True,
                )
            else:
                self.fields["project"] = forms.ModelChoiceField(
                    queryset=Project.objects.filter(managers=user),
                    widget=forms.Select(attrs={"class": "form-control"}),
                    required=True,
                )
        
        if project:
            self.fields["selected_files"] = forms.ModelMultipleChoiceField(
                queryset=ProjectFile.objects.filter(project=project).order_by('category__name', 'original_name'),
                widget=forms.CheckboxSelectMultiple,
                required=False,
                label="Select Project Files to Include in Release",
            )
            if self.instance and self.instance.pk:
                self.fields["selected_files"].initial = self.instance.direct_files.all()
        else:
            self.fields["selected_files"] = forms.ModelMultipleChoiceField(
                queryset=ProjectFile.objects.none(),
                widget=forms.CheckboxSelectMultiple,
                required=False,
                label="Select Project Files to Include in Release",
            )


class ModuleForumPostForm(forms.ModelForm):
    class Meta:
        from .models import ModuleForumPost

        model = ModuleForumPost
        fields = ["content", "attachment"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Start a discussion...",
                }
            ),
            "attachment": forms.FileInput(attrs={"class": "form-control"}),
        }


class RequirementForm(forms.ModelForm):
    class Meta:
        from .models import Requirement

        model = Requirement
        fields = ["req_id", "name", "description"]
        widgets = {
            "req_id": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Requirement ID (Auto-generated if empty)"}
            ),
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Requirement name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Details of the requirement...",
                }
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["req_id"].required = False
