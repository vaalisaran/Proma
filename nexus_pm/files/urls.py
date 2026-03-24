from django.urls import path
from . import views

app_name = 'files'

urlpatterns = [
    path('',                              views.file_list,      name='file_list'),
    path('upload/',                       views.file_upload,    name='file_upload'),
    path('<int:pk>/',                     views.file_detail,    name='file_detail'),
    path('<int:pk>/download/',            views.file_download,  name='file_download'),
    path('<int:pk>/view/',                views.file_view,      name='file_view'),
    path('<int:pk>/edit/',                views.file_edit,      name='file_edit'),
    path('<int:pk>/delete/',              views.file_delete,    name='file_delete'),
    path('project/<int:pk>/',             views.project_files,  name='project_files'),
]
