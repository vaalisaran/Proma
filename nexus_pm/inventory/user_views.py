from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django import forms
from .models import InventoryUser

# Decorator to ensure only admin or managers can access these views
# (Assuming you have an authentication scheme for inventory. Let's use a simple check or rely on session)

def inventory_admin_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        inv_user_id = request.session.get('inv_user_id')
        if not inv_user_id:
            return redirect('accounts:login')
        try:
            user = InventoryUser.objects.get(id=inv_user_id)
            if not getattr(user, 'is_project_manager', False):
                messages.error(request, "Access denied. Admins/Managers only.")
                return redirect('inventory:dashboard')
        except InventoryUser.DoesNotExist:
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

class InventoryUserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank to keep current password (edit only)'}), 
        required=False,
        help_text="If adding a new user, you must set a password. If editing, leave blank to keep current."
    )

    class Meta:
        model = InventoryUser
        fields = ['username', 'email', 'role', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not self.instance.pk and not password:
            raise forms.ValidationError("Password is required for new users.")
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


@method_decorator(inventory_admin_required, name='dispatch')
class InventoryUserListView(ListView):
    model = InventoryUser
    template_name = 'inventory/users/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        qs = super().get_queryset().order_by('-created_at')
        query = self.request.GET.get('q')
        role = self.request.GET.get('role')
        if query:
            qs = qs.filter(username__icontains=query)
        if role:
            qs = qs.filter(role=role)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['role_filter'] = self.request.GET.get('role', '')
        context['role_choices'] = InventoryUser._meta.get_field('role').choices
        return context

@method_decorator(inventory_admin_required, name='dispatch')
class InventoryUserCreateView(CreateView):
    model = InventoryUser
    form_class = InventoryUserForm
    template_name = 'inventory/users/user_form.html'
    success_url = reverse_lazy('inventory-user-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Inventory User'
        context['action'] = 'Save'
        return context

    def form_valid(self, form):
        messages.success(self.request, f"User '{form.instance.username}' created successfully.")
        return super().form_valid(form)

@method_decorator(inventory_admin_required, name='dispatch')
class InventoryUserUpdateView(UpdateView):
    model = InventoryUser
    form_class = InventoryUserForm
    template_name = 'inventory/users/user_form.html'
    success_url = reverse_lazy('inventory-user-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Inventory User'
        context['action'] = 'Update'
        return context

    def form_valid(self, form):
        messages.success(self.request, f"User '{form.instance.username}' updated successfully.")
        return super().form_valid(form)

@method_decorator(inventory_admin_required, name='dispatch')
class InventoryUserDeleteView(DeleteView):
    model = InventoryUser
    template_name = 'inventory/users/user_confirm_delete.html'
    success_url = reverse_lazy('inventory-user-list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "User deleted successfully.")
        return super().delete(request, *args, **kwargs)
