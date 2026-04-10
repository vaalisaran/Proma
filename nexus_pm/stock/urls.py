from django.urls import path
from .views import StockInPageView, StockOutPageView, StockIn, StockOut, DownloadBulkStockInTemplate, DownloadBulkStockOutTemplate

urlpatterns = [
    path('in/', StockInPageView.as_view(), name='stock-in-page'),
    path('out/', StockOutPageView.as_view(), name='stock-out-page'),
    path('api/in/', StockIn.as_view(), name='stock-in-api'),
    path('api/out/', StockOut.as_view(), name='stock-out-api'),
    path('template/in/', DownloadBulkStockInTemplate.as_view(), name='download-stock-in-template'),
    path('template/out/', DownloadBulkStockOutTemplate.as_view(), name='download-stock-out-template'),
]
