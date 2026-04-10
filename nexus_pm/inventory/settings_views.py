from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.core.management import call_command
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from tasks.decorators import admin_required
from inventory.models import InventoryUser
import io
import json
import tempfile
import os

PERMISSION_FIELDS = [
    ('can_access_adjustments_page', 'Adjustments: Page Access'),
    ('can_manage_adjustments', 'Adjustments: Manage Actions'),
    ('can_access_serials_page', 'Serials: Page Access'),
    ('can_manage_serials', 'Serials: Manage Actions'),
    ('can_access_limits_page', 'Limits: Page Access'),
    ('can_manage_limits', 'Limits: Manage Actions'),
    ('can_access_alerts_page', 'Alerts: Page Access'),
    ('can_manage_alerts', 'Alerts: Manage Actions'),
    ('can_access_rentals_page', 'Rentals: Page Access'),
    ('can_manage_rentals', 'Rentals: Manage Actions'),
    ('can_access_shortage_page', 'Shortage: Page Access'),
    ('can_manage_shortage_exports', 'Shortage: Export Actions'),
]

@method_decorator(admin_required, name='dispatch')
class DatabaseBackupView(LoginRequiredMixin, View):
    def get(self, request):
        inventory_users = InventoryUser.objects.all().order_by('role', 'username')
        return render(request, 'inventory/settings.html', {
            'inventory_users': inventory_users,
            'permission_fields': PERMISSION_FIELDS,
        })
        
    def post(self, request):
        action = request.POST.get('action')
        
        if action == 'update_controls':
            inventory_users = InventoryUser.objects.all()
            field_names = [field for field, _ in PERMISSION_FIELDS]
            for inventory_user in inventory_users:
                for field_name in field_names:
                    checkbox_name = f"{field_name}_{inventory_user.id}"
                    setattr(inventory_user, field_name, request.POST.get(checkbox_name) == 'on')
                inventory_user.save(update_fields=field_names)
            messages.success(request, 'Inventory user control restrictions updated successfully.')
            return redirect('inventory_settings')

        if action == 'export':
            out = io.StringIO()
            call_command('dumpdata', 'products', 'stock', 'procurement', 'inventory', stdout=out, indent=2)
            response = HttpResponse(out.getvalue(), content_type='application/json')
            response['Content-Disposition'] = 'attachment; filename="inventory_backup.json"'
            return response
            
        elif action == 'import':
            backup_file = request.FILES.get('backup_file')
            if not backup_file:
                messages.error(request, 'Please provide a valid backup json file.')
                return redirect('inventory_settings')
                
            try:
                # Save file to a temporary location to pass to loaddata
                with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp:
                    for chunk in backup_file.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name
                    
                call_command('loaddata', tmp_path)
                os.unlink(tmp_path)
                messages.success(request, 'Database successfully restored from backup!')
            except Exception as e:
                import traceback
                traceback.print_exc()
                messages.error(request, f'Failed to restore backup: {str(e)}')
            
            return redirect('inventory_settings')
            
        return redirect('inventory_settings')
