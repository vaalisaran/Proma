from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Auth
    path('login/',  views.login_view,  name='login'),
    path('inventory_login/',  views.inventory_login,  name='inventory_login'),
    path('logout/', views.logout_view, name='logout'),

    # User Management (Admin only)
    path('users/',                          views.user_list,           name='user_list'),
    path('users/create/',                   views.user_create,         name='user_create'),
    path('users/<int:pk>/',                 views.user_detail,         name='user_detail'),
    path('users/<int:pk>/edit/',            views.user_edit,           name='user_edit'),
    path('users/<int:pk>/reset-password/',  views.user_reset_password, name='user_reset_password'),
    path('users/<int:pk>/delete/',          views.user_delete,         name='user_delete'),
    path('users/<int:pk>/toggle/',          views.user_toggle_active,  name='user_toggle'),
    path('users/<int:pk>/change-role/',     views.change_user_role,    name='user_change_role'),

    # Profile (self)
    path('profile/',         views.profile_view,   name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('settings/',        views.settings_view,  name='settings'),
]
