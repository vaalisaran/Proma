from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/',     admin.site.urls),
    path('accounts/',  include('accounts.urls', namespace='accounts')),
    path('files/',     include('files.urls',    namespace='files')),
    path('finance/',   include('finance.urls',  namespace='finance')),
    path('',           include('tasks.urls',    namespace='tasks')),

    # Inventory Routes
    path('inventory/dashboard/', include('dashboard.urls')),
    path('inventory/stock/', include('stock.urls')),
    path('inventory/main/', include('inventory.urls')),
    path('inventory/products/', include('products.urls')),
    path('inventory/audit/', include('audit.urls')),
    path('inventory/reports/', include('reports.urls')),
    path('inventory/procurement/', include('procurement.urls')),



    path('',           lambda request: redirect('tasks:dashboard'), name='home'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
