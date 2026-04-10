from django.shortcuts import redirect
import logging
logger = logging.getLogger(__name__)

class InventoryAccessMiddleware:
    """
    Middleware that ensures Inventory Users use the dedicated InventoryUser model,
    and isolates them from Project Management.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        
        # Check standard user
        from django.contrib.auth.models import AnonymousUser
        is_pm_user = hasattr(request, 'user') and request.user.is_authenticated and not isinstance(request.user, AnonymousUser)
        
        # Check explicit inventory session
        inv_user_id = request.session.get('inv_user_id')
        inv_user = None
        
        if inv_user_id:
            try:
                from inventory.models import InventoryUser
                inv_user = InventoryUser.objects.get(id=inv_user_id)
            except:
                pass
                
        # 1. Provide Context for Inventory Paths
        if path.startswith('/inventory/') or path.startswith('/api/inventory/'):
            if inv_user:
                # Override request.user to prevent rewriting 100+ lines of codebase!
                request.user = inv_user
            else:
                # Block PM users and anonymous users
                return redirect('accounts:login')
                
        # 2. Block Inventory Users from PM
        if inv_user and not is_pm_user:
            allowed = ['/inventory/', '/api/inventory/', '/admin/', '/accounts/', '/media/', '/static/']
            if not any(path.startswith(prefix) for prefix in allowed):
                return redirect('/inventory/dashboard/')

        response = self.get_response(request)
        return response
