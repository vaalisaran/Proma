from django.urls import path

from .views import (
    DownloadBulkStockInTemplate,
    DownloadBulkStockOutTemplate,
    StockIn,
    StockInPageView,
    StockOut,
    StockOutPageView,
)

urlpatterns = [
    path("in/", StockInPageView.as_view(), name="stock-in-page"),
    path("out/", StockOutPageView.as_view(), name="stock-out-page"),
    path("api/in/", StockIn.as_view(), name="stock-in-api"),
    path("api/out/", StockOut.as_view(), name="stock-out-api"),
    path(
        "template/in/",
        DownloadBulkStockInTemplate.as_view(),
        name="download-stock-in-template",
    ),
    path(
        "template/out/",
        DownloadBulkStockOutTemplate.as_view(),
        name="download-stock-out-template",
    ),
]
