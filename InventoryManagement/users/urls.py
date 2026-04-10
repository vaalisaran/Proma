from django.urls import path
from . import views

urlpatterns = [
    # HTML Auth views (for browser)
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),

    # HTML User Management pages
    path('profiles/', views.UserListView.as_view(), name='profiles-page'),
    path('profiles/add/', views.UserCreateView.as_view(), name='add-user'),
    path('profiles/edit/<int:pk>/', views.UserEditView.as_view(), name='edit-user'),
    path('profiles/delete/<int:pk>/', views.UserDeleteView.as_view(), name='delete-user'),

    path('roles/', views.RoleListView.as_view(), name='roles-page'),
    path('roles/add/', views.RoleCreateView.as_view(), name='add-role'),
    path('roles/edit/<int:pk>/', views.RoleEditView.as_view(), name='edit-role'),
    path('roles/delete/<int:pk>/', views.RoleDeleteView.as_view(), name='delete-role'),
    
    # API endpoints (for programmatic access)
    path('api/roles/', views.RoleListCreate.as_view(), name='roles-api'),
    path('api/profiles/', views.UserProfileListCreate.as_view(), name='user-profiles-api'),
    path('api/users/', views.UserList.as_view(), name='users-api'),
]
