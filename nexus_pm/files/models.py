import os
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


def upload_to(instance, filename):
    """Generate unique upload path: uploads/<year>/<month>/<uuid>/<filename>"""
    ext   = os.path.splitext(filename)[1].lower()
    uid   = uuid.uuid4().hex[:10]
    now   = timezone.now()
    return f"uploads/{now.year}/{now.month:02d}/{uid}/{filename}"


class FileCategory(models.Model):
    """Optional grouping for files within a project."""
    name       = models.CharField(max_length=100)
    project    = models.ForeignKey('tasks.Project', on_delete=models.CASCADE, related_name='file_categories')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'File Categories'
        ordering = ['name']
        unique_together = ('name', 'project')

    def __str__(self):
        return f"{self.project.name} / {self.name}"


class ProjectFile(models.Model):
    """A file uploaded and attached to a project or task."""

    # --- File type detection helpers ---
    IMAGE_EXTS  = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico', '.tiff'}
    PDF_EXTS    = {'.pdf'}
    DOC_EXTS    = {'.doc', '.docx', '.odt', '.rtf', '.txt', '.md', '.rst'}
    SHEET_EXTS  = {'.xls', '.xlsx', '.csv', '.ods'}
    SLIDE_EXTS  = {'.ppt', '.pptx', '.odp'}
    CODE_EXTS   = {'.py', '.js', '.ts', '.html', '.css', '.java', '.cpp', '.c', '.h',
                   '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.sh', '.bat',
                   '.sql', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.r', '.m'}
    ARCHIVE_EXTS = {'.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar', '.tar.gz'}
    VIDEO_EXTS  = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
    AUDIO_EXTS  = {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a'}
    CAD_EXTS    = {'.dwg', '.dxf', '.step', '.stp', '.iges', '.igs', '.stl', '.obj', '.3ds'}

    FILE_TYPE_CHOICES = [
        ('image',    'Image'),
        ('pdf',      'PDF'),
        ('document', 'Document'),
        ('spreadsheet', 'Spreadsheet'),
        ('presentation', 'Presentation'),
        ('code',     'Code / Script'),
        ('archive',  'Archive'),
        ('video',    'Video'),
        ('audio',    'Audio'),
        ('cad',      'CAD / 3D'),
        ('other',    'Other'),
    ]

    # Core fields
    file        = models.FileField(upload_to=upload_to, max_length=500)
    original_name = models.CharField(max_length=300)   # original filename before upload
    file_size   = models.PositiveBigIntegerField(default=0)  # bytes
    file_type   = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default='other')
    extension   = models.CharField(max_length=20, blank=True)
    mime_type   = models.CharField(max_length=100, blank=True)

    # Relations
    project     = models.ForeignKey('tasks.Project', on_delete=models.CASCADE,
                                    related_name='files', null=True, blank=True)
    module      = models.ForeignKey('tasks.ProjectModule', on_delete=models.SET_NULL,
                                    related_name='files', null=True, blank=True)
    release     = models.ForeignKey('tasks.Release', on_delete=models.SET_NULL,
                                    related_name='direct_files', null=True, blank=True)
    task        = models.ForeignKey('tasks.Task', on_delete=models.SET_NULL,
                                    related_name='files', null=True, blank=True)
    category    = models.ForeignKey(FileCategory, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='files')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, related_name='uploaded_files')

    # Metadata
    title       = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    is_public   = models.BooleanField(default=False,
                  help_text='If True, all project members can download; else only uploader and admin')
    version     = models.PositiveSmallIntegerField(default=1)
    parent_file = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='versions', verbose_name='Previous Version')
    download_count = models.PositiveIntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Project File'

    def __str__(self):
        return self.display_name

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def display_name(self):
        return self.title or self.original_name

    @property
    def file_size_display(self):
        size = self.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 ** 2:
            return f"{size/1024:.1f} KB"
        elif size < 1024 ** 3:
            return f"{size/1024**2:.1f} MB"
        return f"{size/1024**3:.1f} GB"

    @property
    def icon_class(self):
        return {
            'image':        'fa-file-image',
            'pdf':          'fa-file-pdf',
            'document':     'fa-file-word',
            'spreadsheet':  'fa-file-excel',
            'presentation': 'fa-file-powerpoint',
            'code':         'fa-file-code',
            'archive':      'fa-file-archive',
            'video':        'fa-file-video',
            'audio':        'fa-file-audio',
            'cad':          'fa-cube',
        }.get(self.file_type, 'fa-file')

    @property
    def icon_color(self):
        return {
            'image':        '#06b6d4',
            'pdf':          '#ef4444',
            'document':     '#4f8ef7',
            'spreadsheet':  '#22c55e',
            'presentation': '#f97316',
            'code':         '#a855f7',
            'archive':      '#f59e0b',
            'video':        '#ec4899',
            'audio':        '#8b5cf6',
            'cad':          '#64748b',
        }.get(self.file_type, '#7a8aaa')

    @property
    def is_previewable(self):
        """Can be shown inline in the browser."""
        return self.file_type in ('image', 'pdf') or (
            self.file_type == 'code' and self.file_size < 500_000
        ) or (
            self.file_type == 'document' and self.extension in {'.txt', '.md', '.rst'}
            and self.file_size < 500_000
        )

    @property
    def is_text_viewable(self):
        return self.file_type == 'code' or self.extension in {'.txt', '.md', '.rst', '.log', '.ini', '.cfg', '.toml', '.yaml', '.yml', '.json', '.xml', '.csv'}

    @property
    def is_image(self):
        return self.file_type == 'image'

    @property
    def is_pdf(self):
        return self.file_type == 'pdf'

    # ── Class methods ─────────────────────────────────────────────────────────

    @classmethod
    def detect_file_type(cls, extension):
        ext = extension.lower()
        if ext in cls.IMAGE_EXTS:   return 'image'
        if ext in cls.PDF_EXTS:     return 'pdf'
        if ext in cls.DOC_EXTS:     return 'document'
        if ext in cls.SHEET_EXTS:   return 'spreadsheet'
        if ext in cls.SLIDE_EXTS:   return 'presentation'
        if ext in cls.CODE_EXTS:    return 'code'
        if ext in cls.ARCHIVE_EXTS: return 'archive'
        if ext in cls.VIDEO_EXTS:   return 'video'
        if ext in cls.AUDIO_EXTS:   return 'audio'
        if ext in cls.CAD_EXTS:     return 'cad'
        return 'other'

    def save(self, *args, **kwargs):
        if self.file and not self.pk:
            name = os.path.basename(self.file.name)
            if not self.original_name:
                self.original_name = name
            ext = os.path.splitext(name)[1].lower()
            self.extension  = ext
            self.file_type  = self.detect_file_type(ext)
            self.file_size  = self.file.size
        super().save(*args, **kwargs)


class FileComment(models.Model):
    """Comment thread on a file."""
    file       = models.ForeignKey(ProjectFile, on_delete=models.CASCADE, related_name='comments')
    author     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author} on {self.file}"


class DocumentAccessRight(models.Model):
    """Explicit access rights for a file or a knowledge base note."""
    file = models.ForeignKey(ProjectFile, on_delete=models.CASCADE, null=True, blank=True, related_name='access_rights')
    kb_note = models.ForeignKey('tasks.KnowledgeBaseNote', on_delete=models.CASCADE, null=True, blank=True, related_name='access_rights')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='document_access_rights')
    can_view = models.BooleanField(default=True)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        doc = self.file or self.kb_note
        return f"Access for {self.user} on {doc}"
