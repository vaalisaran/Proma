from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from inventory.models import InventoryUser
from tasks.decorators import admin_required


@method_decorator(admin_required, name="dispatch")
class InventoryUserManagementView(View):
    PERMISSION_FIELDS = [
        "can_access_adjustments_page",
        "can_manage_adjustments",
        "can_access_serials_page",
        "can_manage_serials",
        "can_access_limits_page",
        "can_manage_limits",
        "can_access_alerts_page",
        "can_manage_alerts",
        "can_access_rentals_page",
        "can_manage_rentals",
        "can_access_shortage_page",
        "can_manage_shortage_exports",
    ]

    def get(self, request):
        search = request.GET.get("q", "").strip()
        role_filter = request.GET.get("role", "").strip()
        status_filter = request.GET.get("status", "").strip()

        users = InventoryUser.objects.all().order_by("-created_at")
        if search:
            users = users.filter(
                Q(username__icontains=search) | Q(email__icontains=search)
            )
        if role_filter:
            users = users.filter(role=role_filter)
        if status_filter == "active":
            users = users.filter(is_active=True)
        elif status_filter == "inactive":
            users = users.filter(is_active=False)

        paginator = Paginator(users, 20)
        page_obj = paginator.get_page(request.GET.get("page"))

        return render(
            request,
            "inventory/users_management.html",
            {
                "users": page_obj.object_list,
                "page_obj": page_obj,
                "search": search,
                "role_filter": role_filter,
                "status_filter": status_filter,
            },
        )

    def post(self, request):
        action = request.POST.get("action")

        if action == "create":
            username = request.POST.get("username", "").strip()
            password = request.POST.get("password", "").strip()
            email = request.POST.get("email", "").strip()
            role = request.POST.get("role", "staff").strip()

            if not username or not password:
                messages.error(request, "Username and password are required.")
                return redirect("inventory-users-management")
            if InventoryUser.objects.filter(username=username).exists():
                messages.error(request, "Username already exists.")
                return redirect("inventory-users-management")

            user = InventoryUser.objects.create(
                username=username,
                email=email or None,
                role=role,
                is_active=True,
            )
            user.set_password(password)
            messages.success(request, f'Inventory user "{username}" created.')
            return redirect("inventory-users-management")

        user_id = request.POST.get("user_id")
        target_user = get_object_or_404(InventoryUser, id=user_id)

        if action == "update":
            target_user.email = request.POST.get("email", "").strip() or None
            target_user.role = request.POST.get("role", target_user.role).strip()
            target_user.is_active = request.POST.get("is_active") == "on"
            update_fields = ["email", "role", "is_active"]
            for field_name in self.PERMISSION_FIELDS:
                field_value = request.POST.get(field_name) == "on"
                setattr(target_user, field_name, field_value)
                update_fields.append(field_name)
            target_user.save(update_fields=update_fields)
            new_password = request.POST.get("password", "").strip()
            if new_password:
                target_user.set_password(new_password)
            messages.success(request, f'Updated "{target_user.username}".')
            return redirect("inventory-users-management")

        if action == "toggle_active":
            if target_user.id == request.user.id:
                messages.error(request, "You cannot deactivate your own account.")
                return redirect("inventory-users-management")
            target_user.is_active = not target_user.is_active
            target_user.save(update_fields=["is_active"])
            messages.success(request, f'"{target_user.username}" status updated.')
            return redirect("inventory-users-management")

        if action == "delete":
            if target_user.id == request.user.id:
                messages.error(request, "You cannot delete your own account.")
                return redirect("inventory-users-management")
            username = target_user.username
            target_user.delete()
            messages.success(request, f'Inventory user "{username}" deleted.')
            return redirect("inventory-users-management")

        messages.error(request, "Invalid action.")
        return redirect("inventory-users-management")
