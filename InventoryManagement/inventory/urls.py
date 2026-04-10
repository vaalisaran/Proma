from django.urls import path
from .views import (
    InventoryAdjustmentPageView, SerialNumbersPageView, QuantityLimitsPageView, AlertsPageView,
    InventoryAdjustmentAPI, SerialNumbersAPI, QuantityLimitsAPI, QuantityLimitDetailAPI,
    AlertsAPI, AlertDetailAPI, AcknowledgeAlertAPI, ResolveAlertAPI, RentalManagementView, set_standard_limit, inventory_shortage_view, inventory_shortage_export_csv, inventory_shortage_export_pdf
)

urlpatterns = [
    # HTML page routes
    path('adjustments/', InventoryAdjustmentPageView.as_view(), name='inventory-adjustments-page'),
    path('serials/', SerialNumbersPageView.as_view(), name='inventory-serials-page'),
    path('limits/', QuantityLimitsPageView.as_view(), name='inventory-limits-page'),
    path('alerts/', AlertsPageView.as_view(), name='inventory-alerts-page'),
    
    # API routes
    path('adjustments/', InventoryAdjustmentAPI.as_view(), name='inventory-adjustments-api'),
    path('serials/', SerialNumbersAPI.as_view(), name='inventory-serials-api'),
    path('limits/', QuantityLimitsAPI.as_view(), name='inventory-limits-api'),
    path('limits/<int:pk>/', QuantityLimitDetailAPI.as_view(), name='inventory-limit-detail-api'),
    path('alerts/', AlertsAPI.as_view(), name='inventory-alerts-api'),
    path('alerts/<int:pk>/', AlertDetailAPI.as_view(), name='inventory-alert-detail-api'),
    path('alerts/<int:alert_id>/acknowledge/', AcknowledgeAlertAPI.as_view(), name='acknowledge-alert-api'),
    path('alerts/<int:alert_id>/resolve/', ResolveAlertAPI.as_view(), name='resolve-alert-api'),
    path('rentals/', RentalManagementView.as_view(), name='rental-management'),
]

urlpatterns += [
    path('limits/standard/', set_standard_limit, name='set-standard-limit'),
    path('shortage/', inventory_shortage_view, name='inventory-shortage-page'),
    path('shortage/export/csv/', inventory_shortage_export_csv, name='inventory-shortage-export-csv'),
    path('shortage/export/pdf/', inventory_shortage_export_pdf, name='inventory-shortage-export-pdf'),
]
