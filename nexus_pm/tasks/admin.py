from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from .models import Project, Task, Comment, Notification, BugReport, CalendarEvent


# ─── Actions ─────────────────────────────────────────────────────────────────

@admin.action(description="Mark selected tasks as Done")
def mark_tasks_done(modeladmin, request, queryset):
    updated = queryset.update(status='done')
    messages.success(request, f"✅ {updated} task(s) marked as Done.")

@admin.action(description="Mark selected projects as Active")
def mark_projects_active(modeladmin, request, queryset):
    updated = queryset.update(status='active')
    messages.success(request, f"✅ {updated} project(s) set to Active.")

@admin.action(description="Mark selected notifications as Read")
def mark_notifications_read(modeladmin, request, queryset):
    updated = queryset.update(is_read=True)
    messages.success(request, f"✅ {updated} notification(s) marked read.")


# ─── Project Admin ────────────────────────────────────────────────────────────

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'module', 'status_badge', 'priority_badge', 'progress_bar', 'manager', 'member_count', 'start_date', 'end_date']
    list_filter = ['module', 'status', 'priority']
    search_fields = ['name', 'description']
    raw_id_fields = ['manager']
    filter_horizontal = ['members']
    date_hierarchy = 'start_date'
    actions = [mark_projects_active]
    list_per_page = 20

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {'active': '#22c55e', 'completed': '#6366f1', 'on_hold': '#f59e0b', 'cancelled': '#ef4444', 'planning': '#06b6d4'}
        color = colors.get(obj.status, '#6b7280')
        return format_html('<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>', color, obj.get_status_display())

    @admin.display(description='Priority')
    def priority_badge(self, obj):
        colors = {'critical': '#ef4444', 'high': '#f97316', 'medium': '#f59e0b', 'low': '#22c55e'}
        color = colors.get(obj.priority, '#6b7280')
        return format_html('<span style="color:{};font-weight:600;">{}</span>', color, obj.get_priority_display())

    @admin.display(description='Progress')
    def progress_bar(self, obj):
        p = obj.progress or 0
        color = '#22c55e' if p >= 75 else '#f59e0b' if p >= 40 else '#ef4444'
        return format_html(
            '<div style="background:#1e293b;border-radius:4px;height:8px;width:80px;">'
            '<div style="background:{};border-radius:4px;height:8px;width:{}%;"></div>'
            '</div> {}%', color, min(p, 100), p
        )

    @admin.display(description='Members')
    def member_count(self, obj):
        return obj.members.count()


# ─── Task Admin ───────────────────────────────────────────────────────────────

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'task_type', 'status_badge', 'priority_badge', 'assigned_to', 'due_date', 'is_overdue_badge']
    list_filter = ['status', 'priority', 'task_type', 'project']
    search_fields = ['title', 'description']
    raw_id_fields = ['project', 'assigned_to', 'created_by']
    date_hierarchy = 'created_at'
    actions = [mark_tasks_done]
    list_per_page = 25

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {'todo': '#6b7280', 'in_progress': '#3b82f6', 'review': '#a855f7', 'done': '#22c55e', 'cancelled': '#ef4444'}
        color = colors.get(obj.status, '#6b7280')
        return format_html('<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>', color, obj.get_status_display())

    @admin.display(description='Priority')
    def priority_badge(self, obj):
        colors = {'critical': '#ef4444', 'high': '#f97316', 'medium': '#f59e0b', 'low': '#22c55e'}
        color = colors.get(obj.priority, '#6b7280')
        return format_html('<span style="color:{};font-weight:600;">{}</span>', color, obj.get_priority_display())

    @admin.display(description='Overdue', boolean=True)
    def is_overdue_badge(self, obj):
        return obj.is_overdue


# ─── Comment Admin ────────────────────────────────────────────────────────────

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['task', 'author', 'content_preview', 'created_at']
    raw_id_fields = ['task', 'author']
    search_fields = ['content', 'author__username', 'task__title']
    list_per_page = 30

    @admin.display(description='Content')
    def content_preview(self, obj):
        return obj.content[:60] + '...' if len(obj.content) > 60 else obj.content


# ─── Notification Admin ───────────────────────────────────────────────────────

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'notification_type', 'title', 'read_badge', 'created_at']
    list_filter = ['notification_type', 'is_read']
    search_fields = ['title', 'message', 'recipient__username']
    actions = [mark_notifications_read]
    list_per_page = 30

    @admin.display(description='Read')
    def read_badge(self, obj):
        if obj.is_read:
            return format_html('<span style="color:#22c55e;">✅ Read</span>')
        return format_html('<span style="color:#f59e0b;">🔔 Unread</span>')


# ─── Bug Report Admin ─────────────────────────────────────────────────────────

@admin.register(BugReport)
class BugReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'severity_badge', 'status_badge', 'reported_by', 'created_at']
    list_filter = ['severity', 'status', 'project']
    search_fields = ['title', 'description']
    list_per_page = 25

    @admin.display(description='Severity')
    def severity_badge(self, obj):
        colors = {'critical': '#ef4444', 'high': '#f97316', 'medium': '#f59e0b', 'low': '#22c55e'}
        color = colors.get(obj.severity, '#6b7280')
        return format_html('<span style="color:{};font-weight:600;">{}</span>', color, obj.get_severity_display())

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {'open': '#ef4444', 'in_progress': '#3b82f6', 'resolved': '#22c55e', 'closed': '#6b7280'}
        color = colors.get(obj.status, '#6b7280')
        return format_html('<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>', color, obj.get_status_display())


# ─── Calendar Event Admin ─────────────────────────────────────────────────────

@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ['title', 'event_type', 'start_datetime', 'end_datetime', 'created_by']
    list_filter = ['event_type']
    search_fields = ['title', 'description']
    list_per_page = 25
