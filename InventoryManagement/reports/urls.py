from django.urls import path
from .views import StatisticsReportView, statistics_report_export

urlpatterns = [
    path('statistics/', StatisticsReportView.as_view(), name='statistics-report'),
    path('statistics/export/<str:format>/', statistics_report_export, name='statistics-report-export'),
] 