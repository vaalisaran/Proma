from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.views import View
from .models import Role, UserProfile
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from .serializers import RoleSerializer, UserProfileSerializer
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth.models import Permission

User = get_user_model()

def admin_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not (request.user.role and request.user.role.name == 'Admin'):
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('dashboard-overview')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard-overview')
        return render(request, 'users/login.html')

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard-overview')
        else:
            messages.error(request, 'Invalid username or password')
            return render(request, 'users/login.html')

class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('login')

class SignupView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard-overview')
        return render(request, 'users/signup.html')

    def post(self, request):
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        if password1 != password2:
            messages.error(request, 'Passwords do not match')
            return render(request, 'users/signup.html')
        if UserProfile.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'users/signup.html')
        user = UserProfile.objects.create_user(username=username, password=password1)
        login(request, user)
        return redirect('dashboard-overview')

class UserProfileView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
        return render(request, 'users/profile.html', {'user': request.user})

class RolePageView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
        roles = Role.objects.all()
        return render(request, 'users/roles.html', {'roles': roles})

class UserProfilePageView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
        profiles = UserProfile.objects.all()
        return render(request, 'users/profiles.html', {'profiles': profiles})

class RoleListCreate(ListCreateAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]

class UserProfileListCreate(ListCreateAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

class UserList(ListCreateAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

@method_decorator(admin_required, name='dispatch')
class UserListView(View):
    def get(self, request):
        users = User.objects.select_related('role').all()
        return render(request, 'users/profiles.html', {'users': users})

@method_decorator(admin_required, name='dispatch')
class UserCreateView(View):
    def get(self, request):
        roles = Role.objects.all()
        return render(request, 'users/add_user.html', {'roles': roles})
    def post(self, request):
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role_id = request.POST.get('role')
        profile_image = request.FILES.get('profile_image')
        role = Role.objects.get(id=role_id) if role_id else None
        user = User.objects.create_user(username=username, email=email, password=password, role=role, profile_image=profile_image)
        messages.success(request, 'User added successfully!')
        return redirect('profiles-page')

@method_decorator(admin_required, name='dispatch')
class UserEditView(View):
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        roles = Role.objects.all()
        return render(request, 'users/edit_user.html', {'user_obj': user, 'roles': roles})
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        role_id = request.POST.get('role')
        user.role = Role.objects.get(id=role_id) if role_id else None
        if request.FILES.get('profile_image'):
            user.profile_image = request.FILES.get('profile_image')
        if request.POST.get('password'):
            user.set_password(request.POST.get('password'))
        user.save()
        messages.success(request, 'User updated successfully!')
        return redirect('profiles-page')

@method_decorator(admin_required, name='dispatch')
class UserDeleteView(View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.delete()
        messages.success(request, 'User deleted successfully!')
        return redirect('profiles-page')

@method_decorator(admin_required, name='dispatch')
class RoleListView(View):
    def get(self, request):
        roles = Role.objects.all()
        return render(request, 'users/roles.html', {'roles': roles})

@method_decorator(admin_required, name='dispatch')
class RoleCreateView(View):
    def get(self, request):
        permissions = Permission.objects.all()
        return render(request, 'users/add_role.html', {'permissions': permissions})
    def post(self, request):
        name = request.POST.get('name')
        description = request.POST.get('description')
        role = Role.objects.create(name=name, description=description)
        perms = request.POST.getlist('permissions')
        if perms:
            role.permissions.set(perms)
        messages.success(request, 'Role added successfully!')
        return redirect('roles-page')

@method_decorator(admin_required, name='dispatch')
class RoleEditView(View):
    def get(self, request, pk):
        role = get_object_or_404(Role, pk=pk)
        permissions = Permission.objects.all()
        return render(request, 'users/edit_role.html', {'role': role, 'permissions': permissions})
    def post(self, request, pk):
        role = get_object_or_404(Role, pk=pk)
        role.name = request.POST.get('name')
        role.description = request.POST.get('description')
        perms = request.POST.getlist('permissions')
        if perms is not None:
            role.permissions.set(perms)
        role.save()
        messages.success(request, 'Role updated successfully!')
        return redirect('roles-page')

@method_decorator(admin_required, name='dispatch')
class RoleDeleteView(View):
    def post(self, request, pk):
        role = get_object_or_404(Role, pk=pk)
        role.delete()
        messages.success(request, 'Role deleted successfully!')
        return redirect('roles-page')
