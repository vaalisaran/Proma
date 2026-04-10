from django.urls import path
from .views import ProcurementUploadView, ProcurementRestockView, send_all_alerts

urlpatterns = [
    path('upload/', ProcurementUploadView.as_view(), name='procurement-upload'),
    path('restock/', ProcurementRestockView.as_view(), name='procurement-restock'),
    path('send-all-alerts/', send_all_alerts, name='send-all-alerts'),
] 