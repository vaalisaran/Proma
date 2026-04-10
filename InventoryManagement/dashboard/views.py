from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from products.models import Product
from stock.models import StockEntry
from inventory.models import InventoryAdjustment
from django.db import models

class DashboardOverview(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
        # Placeholder data for dashboard KPIs and stock levels
        data = {
            "total_products": 100,
            "total_stock": 5000,
            "alerts": [],
            "kpis": {
                "stock_turnover": 5.2,
                "shrinkage_rate": 0.02,
            }
        }
        return render(request, 'dashboard/overview.html', data)

class DashboardPageView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
        total_products = Product.objects.count()
        total_stock_entries = StockEntry.objects.aggregate(total=models.Sum('quantity'))['total'] or 0
        increase_adj = InventoryAdjustment.objects.filter(adjustment_type='increase').aggregate(total=models.Sum('quantity'))['total'] or 0
        decrease_adj = InventoryAdjustment.objects.filter(adjustment_type='decrease').aggregate(total=models.Sum('quantity'))['total'] or 0
        total_stock = total_stock_entries + increase_adj - decrease_adj
        # Calculate overall stock turnover and shrinkage rate for all products
        total_stock_in = StockEntry.objects.filter(entry_type='in').aggregate(total=models.Sum('quantity'))['total'] or 0
        total_stock_out = StockEntry.objects.filter(entry_type='out').aggregate(total=models.Sum('quantity'))['total'] or 0
        current_total_stock = total_stock_entries + increase_adj - decrease_adj
        average_inventory = ((total_stock_in + current_total_stock) / 2) if (total_stock_in + current_total_stock) > 0 else 1
        stock_turnover = round(total_stock_out / average_inventory, 2) if average_inventory else 0
        positive_adj = InventoryAdjustment.objects.filter(adjustment_type='increase').aggregate(total=models.Sum('quantity'))['total'] or 0
        negative_adj = InventoryAdjustment.objects.filter(adjustment_type='decrease').aggregate(total=models.Sum('quantity'))['total'] or 0
        shrinkage_base = total_stock_in + positive_adj
        shrinkage_rate = round((negative_adj / shrinkage_base) * 100, 2) if shrinkage_base else 0
        alerts = []  # Implement alert logic if needed
        context = {
            'total_products': total_products,
            'total_stock': current_total_stock,
            'stock_turnover': stock_turnover,
            'shrinkage_rate': shrinkage_rate,
            'alerts': alerts,
        }
        return render(request, 'dashboard/overview.html', context)
