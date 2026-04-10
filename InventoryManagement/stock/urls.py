from django.urls import path
from . import views

urlpatterns = [
    # HTML pages
    path('', views.StockInPageView.as_view(), name='stock-in-page'),
    path('in/', views.StockInPageView.as_view(), name='stock-in-page'),
    path('out/', views.StockOutPageView.as_view(), name='stock-out-page'),
    
    # API endpoints (for programmatic access)
    path('api/in/', views.StockIn.as_view(), name='stock-in-api'),
    path('api/out/', views.StockOut.as_view(), name='stock-out-api'),
]
