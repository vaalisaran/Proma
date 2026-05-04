from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("search/", views.global_search, name="global_search"),
    path("projects/", views.project_list, name="project_list"),
    path("projects/new/", views.project_create, name="project_create"),
    path("projects/<int:pk>/", views.project_detail, name="project_detail"),
    path("projects/<int:pk>/edit/", views.project_edit, name="project_edit"),
    path("projects/<int:pk>/members/", views.project_members, name="project_members"),
    path("projects/<int:pk>/delete/", views.project_delete, name="project_delete"),
    path(
        "projects/<int:pk>/requirements/new/",
        views.requirement_create,
        name="requirement_create",
    ),
    path(
        "requirements/<int:pk>/edit/",
        views.requirement_edit,
        name="requirement_edit",
    ),
    path(
        "requirements/<int:pk>/delete/",
        views.requirement_delete,
        name="requirement_delete",
    ),
    path("projects/<int:pk>/modules/", views.module_list, name="module_list"),
    path("projects/<int:pk>/modules/new/", views.module_create, name="module_create"),
    path("modules/<int:pk>/", views.module_detail, name="module_detail"),
    path("modules/<int:pk>/edit/", views.module_edit, name="module_edit"),
    path("modules/<int:pk>/delete/", views.module_delete, name="module_delete"),
    path("modules/<int:pk>/members/", views.module_members, name="module_members"),
    path("projects/<int:pk>/releases/", views.release_list, name="release_list"),
    path(
        "projects/<int:pk>/releases/new/", views.release_create, name="release_create"
    ),
    path("releases/<int:pk>/", views.release_detail, name="release_detail"),
    path("releases/<int:pk>/edit/", views.release_edit, name="release_edit"),
    path("releases/<int:pk>/delete/", views.release_delete, name="release_delete"),
    path(
        "releases/<int:pk>/download/", views.release_download, name="release_download"
    ),
    path(
        "releases/<int:pk>/assets/download/",
        views.release_assets_download,
        name="release_assets_download",
    ),
    path("knowledge-base/", views.kb_overview, name="kb_overview"),
    path("knowledge-base/new/", views.kb_create_global, name="kb_create_global"),
    path("projects/<int:pk>/knowledge-base/", views.kb_list, name="kb_list"),
    path("projects/<int:pk>/knowledge-base/new/", views.kb_create, name="kb_create"),
    path("projects/<int:pk>/cicd/", views.project_cicd, name="project_cicd"),
    path("knowledge-base/<int:pk>/", views.kb_detail, name="kb_detail"),
    path("knowledge-base/<int:pk>/edit/", views.kb_edit, name="kb_edit"),
    path("knowledge-base/<int:pk>/access/", views.kb_access, name="kb_access"),
    path("knowledge-base/<int:pk>/delete/", views.kb_delete, name="kb_delete"),
    path("tasks/", views.task_list, name="task_list"),
    path("tasks/new/", views.task_create, name="task_create"),
    path("tasks/<int:pk>/", views.task_detail, name="task_detail"),
    path("tasks/<int:pk>/edit/", views.task_edit, name="task_edit"),
    path("tasks/<int:pk>/delete/", views.task_delete, name="task_delete"),
    path("tasks/<int:pk>/status/", views.task_update_status, name="task_update_status"),
    path("notifications/", views.notifications, name="notifications"),
    path(
        "notifications/<int:pk>/read/",
        views.notification_read,
        name="notification_read",
    ),
    path("bugs/", views.bug_list, name="bug_list"),
    path("bugs/new/", views.bug_create, name="bug_create"),
    path("bugs/<int:pk>/", views.bug_detail, name="bug_detail"),
    path("bugs/<int:pk>/edit/", views.bug_edit, name="bug_edit"),
    path("calendar/", views.calendar_view, name="calendar"),
    path("calendar/event/new/", views.event_create, name="event_create"),
    path("reports/", views.reports, name="reports"),
    path("releases/", views.global_release_list, name="global_release_list"),
    path("api/tasks-for-project/", views.tasks_for_project, name="tasks_for_project"),
    path("api/project-modules/", views.project_modules_api, name="project_modules_api"),
    path(
        "api/project-requirements/",
        views.project_requirements_api,
        name="project_requirements_api",
    ),
    path("api/project-members/", views.project_members_api, name="project_members_api"),
    path("pm-inventory/", views.inventory_list, name="inventory_list"),
    path(
        "projects/<int:pk>/requirements/report/",
        views.requirement_report,
        name="requirement_report",
    ),
    path(
        "projects/<int:pk>/tasks/report/",
        views.task_report,
        name="task_report",
    ),
]
