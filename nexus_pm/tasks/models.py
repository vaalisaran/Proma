from django.conf import settings
from django.db import models
from django.utils import timezone
import random
import string


class Project(models.Model):
    MODULE_CHOICES = [
        ("electronics", "Electronics"),
        ("mechanical", "Mechanical"),
        ("optics", "Optics"),
        ("simulation", "Simulation"),
        ("software", "Software"),
    ]
    STATUS_CHOICES = [
        ("planning", "Planning"),
        ("active", "Active"),
        ("on_hold", "On Hold"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    project_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    module = models.CharField(
        max_length=20, choices=MODULE_CHOICES, null=True, blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planning")
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="medium"
    )
    background_color = models.CharField(max_length=7, default="#ffffff")
    button_color = models.CharField(max_length=7, default="#4f8ef7")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_projects",
    )
    managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="managed_projects"
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="projects"
    )
    progress = models.PositiveIntegerField(default=0)  # 0-100
    deletion_requested_by_admin = models.BooleanField(default=False)
    deletion_requested_by_pm = models.BooleanField(default=False)
    deletion_requested_at = models.DateTimeField(null=True, blank=True)
    image = models.ImageField(upload_to="project_images/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.project_id}] {self.name}" if self.project_id else self.name

    @property
    def is_overdue(self):
        if self.end_date:
            return self.end_date < timezone.now().date() and self.status not in [
                "completed",
                "cancelled",
            ]
        return False

    @property
    def task_count(self):
        return self.tasks.count()

    @property
    def completed_task_count(self):
        return self.tasks.filter(status="done").count()

    def update_progress(self):
        total = self.tasks.count()
        if total == 0:
            self.progress = 0
        else:
            done = self.tasks.filter(status="done").count()
            self.progress = int((done / total) * 100)
        self.save(update_fields=["progress"])

    def save(self, *args, **kwargs):
        if not self.project_id:
            words = self.name.replace("-", " ").split()
            initials = "".join([w[0].upper() for w in words if w and w[0].isalpha()])
            if not initials:
                initials = "".join(random.choices(string.ascii_uppercase, k=4))
            
            while len(initials) < 4:
                initials += random.choice(string.ascii_uppercase)
            initials = initials[:4]
            
            year = timezone.now().year
            count = Project.objects.filter(created_at__year=year).count() + 1
            if self.pk:
                count = Project.objects.filter(created_at__year=self.created_at.year).count()
            
            while True:
                pid = f"{initials}-{year}-{count:04d}"
                if not Project.objects.filter(project_id=pid).exists():
                    self.project_id = pid
                    break
                count += 1
        super().save(*args, **kwargs)


class ProjectModule(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="modules"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.project.name} - {self.name}"


class ModuleMember(models.Model):
    ROLE_CHOICES = [
        ("designer", "Designer"),
        ("developer", "Developer"),
        ("tester", "Tester"),
    ]
    module = models.ForeignKey(
        ProjectModule, on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="module_memberships",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="developer")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("module", "user")

    def __str__(self):
        return f"{self.user} ({self.get_role_display()}) in {self.module.name}"


class Requirement(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="requirements"
    )
    req_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.req_id}] {self.name}" if self.req_id else self.name

    def save(self, *args, **kwargs):
        if not self.req_id and self.project:
            # Use the 4-char project prefix
            project_prefix = self.project.project_id.split('-')[0] if self.project.project_id else "PROJ"
            year = timezone.now().year
            count = Requirement.objects.filter(project=self.project).count() + 1
            while True:
                rid = f"{project_prefix}-REQ-{year}-{count:06d}"
                if not Requirement.objects.filter(req_id=rid).exists():
                    self.req_id = rid
                    break
                count += 1
        super().save(*args, **kwargs)


class Task(models.Model):
    STATUS_CHOICES = [
        ("todo", "To Do"),
        ("in_progress", "In Progress"),
        ("review", "In Review"),
        ("done", "Done"),
        ("blocked", "Blocked"),
    ]
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]
    TYPE_CHOICES = [
        ("task", "Task"),
        ("bug", "Bug"),
        ("feature", "Feature"),
        ("improvement", "Improvement"),
        ("research", "Research"),
    ]

    task_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="tasks", null=True, blank=True
    )
    requirement = models.ForeignKey(
        Requirement,
        on_delete=models.CASCADE,
        related_name="tasks",
        null=True,
        blank=True,
    )
    module = models.ForeignKey(
        "ProjectModule",
        on_delete=models.SET_NULL,
        related_name="tasks",
        null=True,
        blank=True,
    )
    release = models.ForeignKey(
        "Release",
        on_delete=models.SET_NULL,
        related_name="tasks",
        null=True,
        blank=True,
    )
    task_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="task")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="todo")
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="medium"
    )
    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="assigned_tasks"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_tasks",
    )
    parent_task = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subtasks",
    )
    due_date = models.DateField(null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)
    estimated_hours = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    actual_hours = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    tags = models.CharField(
        max_length=500, blank=True, help_text="Comma-separated tags"
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return f"[{self.task_id}] {self.title}" if self.task_id else self.title

    @property
    def is_overdue(self):
        if self.due_date and self.status != "done":
            return self.due_date < timezone.now().date()
        return False

    @property
    def tag_list(self):
        if self.tags:
            return [t.strip() for t in self.tags.split(",") if t.strip()]
        return []

    def save(self, *args, **kwargs):
        if self.status == "done" and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != "done":
            self.completed_at = None
            
        if not self.task_id:
            type_map = {
                "task": "TAS",
                "bug": "BUG",
                "feature": "FEA",
                "improvement": "IMP",
                "research": "RES",
            }
            type_prefix = type_map.get(self.task_type, "TAS")
            
            project_prefix = "GEN"
            if self.project:
                project_prefix = self.project.project_id.split('-')[0] if self.project.project_id else "PROJ"
            
            year = timezone.now().year
            module_num = f"{self.module.pk:04d}" if self.module else "0000"
            
            # Count tasks for this project in this year
            if self.project:
                count = Task.objects.filter(project=self.project).count() + 1
            else:
                count = Task.objects.filter(project__isnull=True).count() + 1

            while True:
                tid = f"{type_prefix}-{project_prefix}-{year}-{module_num}-{count:06d}"
                if not Task.objects.filter(task_id=tid).exists():
                    self.task_id = tid
                    break
                count += 1

        super().save(*args, **kwargs)
        # Update project progress
        if self.project:
            self.project.update_progress()


class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    attachment = models.FileField(upload_to="comments/%Y/%m/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author} on {self.task}"


class Notification(models.Model):
    TYPE_CHOICES = [
        ("task_assigned", "Task Assigned"),
        ("task_updated", "Task Updated"),
        ("task_completed", "Task Completed"),
        ("comment_added", "Comment Added"),
        ("due_soon", "Due Soon"),
        ("overdue", "Overdue"),
        ("project_update", "Project Update"),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_notifications",
    )
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True)
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.notification_type} for {self.recipient}"


class BugReport(models.Model):
    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]
    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
        ("wont_fix", "Won't Fix"),
    ]

    title = models.CharField(max_length=300)
    description = models.TextField()
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="bug_reports",
        null=True,
        blank=True,
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reported_bugs"
    )
    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="assigned_bugs"
    )
    severity = models.CharField(
        max_length=10, choices=SEVERITY_CHOICES, default="medium"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    steps_to_reproduce = models.TextField(blank=True)
    expected_behavior = models.TextField(blank=True)
    actual_behavior = models.TextField(blank=True)
    linked_task = models.ForeignKey(
        Task, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class CalendarEvent(models.Model):
    TYPE_CHOICES = [
        ("milestone", "Milestone"),
        ("meeting", "Meeting"),
        ("deadline", "Deadline"),
        ("review", "Review"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="other")
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True
    )
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    attendees = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="calendar_events"
    )
    meeting_link = models.URLField(max_length=500, blank=True, null=True)
    meeting_password = models.CharField(max_length=100, blank=True, null=True)
    color = models.CharField(max_length=7, default="#6366f1")
    google_event_id = models.CharField(max_length=255, blank=True, null=True)
    caldav_event_path = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_datetime"]

    def __str__(self):
        return self.title


class UserCalendarSettings(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="calendar_settings"
    )
    # CalDAV (Radicale) Settings
    caldav_url = models.URLField(max_length=500, default="https://ssaran.pythonanywhere.com/")
    caldav_user = models.CharField(max_length=100, default="your_username", blank=True, null=True)
    caldav_password = models.CharField(max_length=100, blank=True, null=True)
    caldav_calendar_name = models.CharField(max_length=100, default="IIAP PM")

    # Google Calendar Settings
    google_calendar_id = models.CharField(max_length=255, default="primary")
    google_oauth_token = models.JSONField(blank=True, null=True)
    is_google_synced = models.BooleanField(default=False)
    is_caldav_synced = models.BooleanField(default=False)

    def __str__(self):
        return f"Calendar Settings for {self.user.username}"


class KnowledgeBaseNote(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="kb_notes",
        null=True,
        blank=True,
    )
    module = models.ForeignKey(
        "ProjectModule",
        on_delete=models.SET_NULL,
        related_name="kb_notes",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    content = models.TextField(help_text="Markdown format supported")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.project:

            from django.core.files.base import ContentFile

            from files.models import FileCategory, ProjectFile

            notes_cat, _ = FileCategory.objects.get_or_create(
                name="Notes",
                project=self.project,
                defaults={"created_by": self.author}
            )

            file_name = f"{self.title}.md".replace("/", "-")
            content_bytes = self.content.encode('utf-8')

            existing_file = ProjectFile.objects.filter(
                original_name=file_name,
                project=self.project,
                category=notes_cat
            ).order_by('-version').first()

            if existing_file:
                # To maintain versions, we can create a new version if we wanted, 
                # but to be simple and "updating to the notes file" we just overwrite the FileField
                if existing_file.file:
                    existing_file.file.delete(save=False)
                existing_file.file.save(file_name, ContentFile(content_bytes), save=False)
                existing_file.save()
            else:
                pf = ProjectFile(
                    original_name=file_name,
                    project=self.project,
                    category=notes_cat,
                    uploaded_by=self.author,
                    description=f"Auto-generated from KB Note: {self.title}"
                )
                pf.file.save(file_name, ContentFile(content_bytes), save=False)
                pf.save()


class SystemSettings(models.Model):
    primary_color = models.CharField(max_length=7, default="#4f8ef7")
    font_size = models.CharField(max_length=20, default="14px")
    default_pm_password = models.CharField(max_length=128, default="nexuspm123")

    class Meta:
        verbose_name_plural = "System Settings"

    def __str__(self):
        return "System Settings"

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SystemIssue(models.Model):
    TYPE_CHOICES = [
        ("bug", "Bug"),
        ("feature", "Feature Request"),
    ]
    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]

    title = models.CharField(max_length=300)
    description = models.TextField()
    issue_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="bug")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reported_system_issues",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_system_issues",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_issue_type_display()}: {self.title}"


class PipelineRun(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("passed", "Passed"),
        ("failed", "Failed"),
    ]

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="pipeline_runs"
    )
    name = models.CharField(max_length=200, help_text="e.g. Build & Test")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    trigger_commit = models.CharField(
        max_length=100, blank=True, help_text="Git commit hash"
    )
    triggered_by = models.CharField(
        max_length=100, blank=True, help_text="User or webhook name"
    )
    duration_seconds = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.name} - {self.get_status_display()} ({self.project.name})"


class Release(models.Model):
    TYPE_CHOICES = [
        ("partial", "Partial (Minor/Nightly)"),
        ("phase", "Phase (Major)"),
    ]
    STATUS_CHOICES = [
        ("planning", "Planning"),
        ("active", "Active"),
        ("completed", "Completed"),
    ]

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="releases"
    )
    name = models.CharField(max_length=200, help_text="e.g. May 2025 Release")
    release_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default="partial"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planning")
    description = models.TextField(
        blank=True, help_text="Release notes (Markdown supported)"
    )
    tag_name = models.CharField(
        max_length=50, blank=True, help_text="e.g. v1.0.0"
    )
    target_date = models.DateField(null=True, blank=True)
    release_date = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    is_approved = models.BooleanField(default=False)
    is_draft = models.BooleanField(default=False)
    is_prerelease = models.BooleanField(default=False)

    class Meta:
        ordering = ["-release_date"]
        unique_together = ("project", "name")

    def __str__(self):
        return f"{self.project.name} - {self.name}"


class ReleaseModuleVersion(models.Model):
    release = models.ForeignKey(
        Release, on_delete=models.CASCADE, related_name="module_versions"
    )
    module = models.ForeignKey(
        "ProjectModule", on_delete=models.CASCADE, related_name="release_versions"
    )
    version_string = models.CharField(max_length=50, blank=True)
    file = models.ForeignKey(
        "files.ProjectFile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        unique_together = ("release", "module")

    def __str__(self):
        return f"{self.module.name} ({self.version_string}) for {self.release.name}"


class ModuleForumPost(models.Model):
    module = models.ForeignKey(
        ProjectModule, on_delete=models.CASCADE, related_name="forum_posts"
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    attachment = models.FileField(upload_to="forum_posts/%Y/%m/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Post by {self.author} in {self.module.name}"
