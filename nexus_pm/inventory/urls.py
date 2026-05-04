from django.urls import path

from .settings_views import DatabaseBackupView
from .user_management_views import InventoryUserManagementView
from .views import (
    AcknowledgeAlertAPI,
    AlertDetailAPI,
    AlertsAPI,
    AlertsPageView,
    InventoryAdjustmentAPI,
    InventoryAdjustmentPageView,
    InventoryNotificationsPageView,
    QuantityLimitDetailAPI,
    QuantityLimitsAPI,
    QuantityLimitsPageView,
    RentalManagementView,
    ResolveAlertAPI,
    SerialNumbersAPI,
    SerialNumbersPageView,
    inventory_shortage_export_csv,
    inventory_shortage_export_pdf,
    inventory_shortage_view,
    set_standard_limit,
)

urlpatterns = [
    # HTML page routes
    path("settings/", DatabaseBackupView.as_view(), name="inventory_settings"),
    path(
        "users/",
        InventoryUserManagementView.as_view(),
        name="inventory-users-management",
    ),
    path(
        "adjustments/",
        InventoryAdjustmentPageView.as_view(),
        name="inventory-adjustments-page",
    ),
    path("serials/", SerialNumbersPageView.as_view(), name="inventory-serials-page"),
    path("limits/", QuantityLimitsPageView.as_view(), name="inventory-limits-page"),
    path("alerts/", AlertsPageView.as_view(), name="inventory-alerts-page"),
    path(
        "notifications/",
        InventoryNotificationsPageView.as_view(),
        name="inventory-notifications-page",
    ),
    # API routes
    path(
        "api/adjustments/",
        InventoryAdjustmentAPI.as_view(),
        name="inventory-adjustments-api",
    ),
    path("api/serials/", SerialNumbersAPI.as_view(), name="inventory-serials-api"),
    path("api/limits/", QuantityLimitsAPI.as_view(), name="inventory-limits-api"),
    path(
        "api/limits/<int:pk>/",
        QuantityLimitDetailAPI.as_view(),
        name="inventory-limit-detail-api",
    ),
    path("api/alerts/", AlertsAPI.as_view(), name="inventory-alerts-api"),
    path(
        "api/alerts/<int:pk>/", AlertDetailAPI.as_view(), name="inventory-alert-detail-api"
    ),
    path(
        "alerts/<int:alert_id>/acknowledge/",
        AcknowledgeAlertAPI.as_view(),
        name="acknowledge-alert-api",
    ),
    path(
        "alerts/<int:alert_id>/resolve/",
        ResolveAlertAPI.as_view(),
        name="resolve-alert-api",
    ),
    path("rentals/", RentalManagementView.as_view(), name="rental-management"),
]

urlpatterns += [
    path("limits/standard/", set_standard_limit, name="set-standard-limit"),
    path("shortage/", inventory_shortage_view, name="inventory-shortage-page"),
    path(
        "shortage/export/csv/",
        inventory_shortage_export_csv,
        name="inventory-shortage-export-csv",
    ),
    path(
        "shortage/export/pdf/",
        inventory_shortage_export_pdf,
        name="inventory-shortage-export-pdf",
    ),
]
