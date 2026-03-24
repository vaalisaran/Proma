from django.contrib import admin
from django.utils.html import format_html
from .models import ProjectFile, FileCategory, FileComment


@admin.register(ProjectFile)
class ProjectFileAdmin(admin.ModelAdmin):
    list_display = ['original_name', 'type_badge', 'file_size_display', 'project', 'task', 'uploaded_by', 'download_count', 'created_at']
    list_filter = ['file_type', 'project']
    search_fields = ['original_name', 'title', 'description']
    raw_id_fields = ['project', 'task', 'uploaded_by']
    list_per_page = 25

    @admin.display(description='Type')
    def type_badge(self, obj):
        colors = {
            'image': '#06b6d4', 'document': '#6366f1', 'code': '#a855f7',
            'archive': '#f59e0b', 'video': '#ef4444', 'audio': '#22c55e', 'other': '#6b7280',
        }
        color = colors.get(obj.file_type, '#6b7280')
        return format_html('<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>', color, obj.get_file_type_display())

    @admin.display(description='Size')
    def file_size_display(self, obj):
        try:
            return obj.file_size_display
        except Exception:
            return f"{obj.file_size} bytes"


@admin.register(FileCategory)
class FileCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'created_by']
    search_fields = ['name']


@admin.register(FileComment)
class FileCommentAdmin(admin.ModelAdmin):
    list_display = ['file', 'author', 'content_preview', 'created_at']
    raw_id_fields = ['file', 'author']

    @admin.display(description='Comment')
    def content_preview(self, obj):
        return obj.content[:60] + '...' if len(obj.content) > 60 else obj.content
