from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('dashboard/',                          views.dashboard,           name='dashboard'),
    path('projects/',                           views.project_list,        name='project_list'),
    path('projects/new/',                       views.project_create,      name='project_create'),
    path('projects/<int:pk>/',                  views.project_detail,      name='project_detail'),
    path('projects/<int:pk>/edit/',             views.project_edit,        name='project_edit'),
    path('projects/<int:pk>/members/',          views.project_members,     name='project_members'),
    path('projects/<int:pk>/delete/',           views.project_delete,      name='project_delete'),
    path('tasks/',                              views.task_list,           name='task_list'),
    path('tasks/new/',                          views.task_create,         name='task_create'),
    path('tasks/<int:pk>/',                     views.task_detail,         name='task_detail'),
    path('tasks/<int:pk>/edit/',                views.task_edit,           name='task_edit'),
    path('tasks/<int:pk>/delete/',              views.task_delete,         name='task_delete'),
    path('tasks/<int:pk>/status/',              views.task_update_status,  name='task_update_status'),
    path('notifications/',                      views.notifications,       name='notifications'),
    path('notifications/<int:pk>/read/',        views.notification_read,   name='notification_read'),
    path('bugs/',                               views.bug_list,            name='bug_list'),
    path('bugs/new/',                           views.bug_create,          name='bug_create'),
    path('bugs/<int:pk>/',                      views.bug_detail,          name='bug_detail'),
    path('bugs/<int:pk>/edit/',                 views.bug_edit,            name='bug_edit'),
    path('calendar/',                           views.calendar_view,       name='calendar'),
    path('calendar/event/new/',                 views.event_create,        name='event_create'),
    path('reports/',                            views.reports,             name='reports'),
    path('api/tasks-for-project/',              views.tasks_for_project,   name='tasks_for_project'),
    path('api/project-members/',                views.project_members_api, name='project_members_api'),
]
