from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.decorators import login_required
from dashboard.views import DashboardPageView
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # HTML page routes (main application)
    path('', login_required(DashboardPageView.as_view()), name='dashboard-overview'),
    path('dashboard/', include('dashboard.urls')),
    path('stock/', include('stock.urls')),
    path('inventory/', include('inventory.urls')),
    path('products/', include('products.urls')),
    path('users/', include('users.urls')),
    path('audit/', include('audit.urls')),
    path('reports/', include('reports.urls')),
    path('procurement/', include('procurement.urls')),

    # API routes for apps (separate from HTML pages)
    path('api/dashboard/', include('dashboard.urls')),
    path('api/stock/', include('stock.urls')),
    path('api/inventory/', include('inventory.urls')),
    path('api/products/', include('products.urls')),
    path('api/users/', include('users.urls')),
    path('api/audit/', include('audit.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
