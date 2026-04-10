from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.core.management import call_command
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from tasks.decorators import admin_required
import io
import json
import tempfile
import os

@method_decorator(admin_required, name='dispatch')
class DatabaseBackupView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'inventory/settings.html')
        
    def post(self, request):
        action = request.POST.get('action')
        
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
