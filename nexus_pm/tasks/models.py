from django.db import models
from django.conf import settings
from django.utils import timezone


class Project(models.Model):
    MODULE_CHOICES = [
        ('electronics', 'Electronics'),
        ('mechanical', 'Mechanical'),
        ('optics', 'Optics'),
        ('simulation', 'Simulation'),
        ('software', 'Software'),
    ]
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    module = models.CharField(max_length=20, choices=MODULE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    start_date = models.DateField()
    end_date = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_projects'
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='managed_projects'
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='projects'
    )
    progress = models.PositiveIntegerField(default=0)  # 0-100
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_overdue(self):
        return self.end_date < timezone.now().date() and self.status not in ['completed', 'cancelled']

    @property
    def task_count(self):
        return self.tasks.count()

    @property
    def completed_task_count(self):
        return self.tasks.filter(status='done').count()

    def update_progress(self):
        total = self.tasks.count()
        if total == 0:
            self.progress = 0
        else:
            done = self.tasks.filter(status='done').count()
            self.progress = int((done / total) * 100)
        self.save(update_fields=['progress'])


class Task(models.Model):
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('review', 'In Review'),
        ('done', 'Done'),
        ('blocked', 'Blocked'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    TYPE_CHOICES = [
        ('task', 'Task'),
        ('bug', 'Bug'),
        ('feature', 'Feature'),
        ('improvement', 'Improvement'),
        ('research', 'Research'),
    ]

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    task_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='task')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_tasks'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_tasks'
    )
    parent_task = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='subtasks'
    )
    due_date = models.DateField(null=True, blank=True)
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    actual_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    tags = models.CharField(max_length=500, blank=True, help_text='Comma-separated tags')
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        if self.due_date and self.status != 'done':
            return self.due_date < timezone.now().date()
        return False

    @property
    def tag_list(self):
        if self.tags:
            return [t.strip() for t in self.tags.split(',') if t.strip()]
        return []

    def save(self, *args, **kwargs):
        if self.status == 'done' and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != 'done':
            self.completed_at = None
        super().save(*args, **kwargs)
        # Update project progress
        self.project.update_progress()


class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author} on {self.task}"


class Notification(models.Model):
    TYPE_CHOICES = [
        ('task_assigned', 'Task Assigned'),
        ('task_updated', 'Task Updated'),
        ('task_completed', 'Task Completed'),
        ('comment_added', 'Comment Added'),
        ('due_soon', 'Due Soon'),
        ('overdue', 'Overdue'),
        ('project_update', 'Project Update'),
    ]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='sent_notifications')
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} for {self.recipient}"


class BugReport(models.Model):
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('wont_fix', "Won't Fix"),
    ]

    title = models.CharField(max_length=300)
    description = models.TextField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='bug_reports')
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reported_bugs')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_bugs')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    steps_to_reproduce = models.TextField(blank=True)
    expected_behavior = models.TextField(blank=True)
    actual_behavior = models.TextField(blank=True)
    linked_task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class CalendarEvent(models.Model):
    TYPE_CHOICES = [
        ('milestone', 'Milestone'),
        ('meeting', 'Meeting'),
        ('deadline', 'Deadline'),
        ('review', 'Review'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='other')
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    attendees = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='calendar_events')
    color = models.CharField(max_length=7, default='#6366f1')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_datetime']

    def __str__(self):
        return self.title
