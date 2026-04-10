from django.shortcuts import render, redirect
from django.views import View
from products.models import Product, Category
from stock.models import StockEntry
from inventory.models import Rental, InventoryAdjustment, Alert
from django.db.models import Sum, Count
import pandas as pd
from django.http import HttpResponse
from django.template.loader import render_to_string
from io import BytesIO
from django.utils.html import strip_tags
from django.utils import timezone

# Create your views here.

class StatisticsReportView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')

        # Overall stats
        total_products = Product.objects.count()
        total_stock_in = StockEntry.objects.filter(entry_type='in').aggregate(total=Sum('quantity'))['total'] or 0
        total_stock_out = StockEntry.objects.filter(entry_type='out').aggregate(total=Sum('quantity'))['total'] or 0
        current_stock = total_stock_in - total_stock_out
        total_rentals = Rental.objects.count()
        active_rentals = Rental.objects.filter(status='active').count()
        overdue_rentals = Rental.objects.filter(status='overdue').count()
        total_adjustments = InventoryAdjustment.objects.count()
        total_alerts = Alert.objects.count()
        active_alerts = Alert.objects.filter(status='active').count()

        # Product breakdown by category
        category_breakdown = list(
            Category.objects.annotate(product_count=Count('products'))
            .values('name', 'product_count')
            .order_by('-product_count')
        )

        # Stock in/out by month (last 12 months)
        now = timezone.now()
        months = []
        for i in range(11, -1, -1):
            month = (now.replace(day=1) - timezone.timedelta(days=30 * i)).replace(day=1)
            months.append(month)
        months = sorted(set([m.replace(day=1) for m in months]))
        month_labels = [m.strftime('%b %Y') for m in months]
        stock_in_by_month = [
            StockEntry.objects.filter(entry_type='in', timestamp__year=m.year, timestamp__month=m.month)
            .aggregate(total=Sum('quantity'))['total'] or 0
            for m in months
        ]
        stock_out_by_month = [
            StockEntry.objects.filter(entry_type='out', timestamp__year=m.year, timestamp__month=m.month)
            .aggregate(total=Sum('quantity'))['total'] or 0
            for m in months
        ]

        # Rentals by status
        rental_status_breakdown = list(Rental.objects.values('status').annotate(count=Count('id')))
        rental_status_labels = [r['status'].title() for r in rental_status_breakdown]
        rental_status_counts = [r['count'] for r in rental_status_breakdown]

        # Rentals by product (top 10)
        rental_product_breakdown = list(
            Rental.objects.values('product__name').annotate(count=Count('id')).order_by('-count')[:10]
        )
        rental_product_names = [r['product__name'] for r in rental_product_breakdown]
        rental_product_counts = [r['count'] for r in rental_product_breakdown]

        # Alerts by type
        alert_type_breakdown = list(Alert.objects.values('alert_type').annotate(count=Count('id')))
        alert_type_labels = [a['alert_type'].replace('_', ' ').title() for a in alert_type_breakdown]
        alert_type_counts = [a['count'] for a in alert_type_breakdown]

        # Alerts by product (top 10)
        alert_product_breakdown = list(
            Alert.objects.values('product__name').annotate(count=Count('id')).order_by('-count')[:10]
        )
        alert_product_names = [a['product__name'] for a in alert_product_breakdown]
        alert_product_counts = [a['count'] for a in alert_product_breakdown]

        context = {
            'total_products': total_products,
            'total_stock_in': total_stock_in,
            'total_stock_out': total_stock_out,
            'current_stock': current_stock,
            'total_rentals': total_rentals,
            'active_rentals': active_rentals,
            'overdue_rentals': overdue_rentals,
            'total_adjustments': total_adjustments,
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'category_breakdown': category_breakdown,
            'month_labels': month_labels,
            'stock_in_by_month': stock_in_by_month,
            'stock_out_by_month': stock_out_by_month,
            'rental_status_breakdown': rental_status_breakdown,
            'rental_product_breakdown': rental_product_breakdown,
            'alert_type_breakdown': alert_type_breakdown,
            'alert_product_breakdown': alert_product_breakdown,
            # Chart data
            'category_names': [c['name'] for c in category_breakdown],
            'category_counts': [c['product_count'] for c in category_breakdown],
            'rental_status_labels': rental_status_labels,
            'rental_status_counts': rental_status_counts,
            'rental_product_names': rental_product_names,
            'rental_product_counts': rental_product_counts,
            'alert_type_labels': alert_type_labels,
            'alert_type_counts': alert_type_counts,
            'alert_product_names': alert_product_names,
            'alert_product_counts': alert_product_counts,
        }
        return render(request, 'reports/statistics.html', context)

def statistics_report_export(request, format):
    if not request.user.is_authenticated:
        return redirect('login')
    # Gather the same data as in StatisticsReportView
    now = timezone.now()
    months = []
    for i in range(11, -1, -1):
        month = (now.replace(day=1) - timezone.timedelta(days=30*i)).replace(day=1)
        months.append(month)
    months = sorted(set([m.replace(day=1) for m in months]))
    month_labels = [m.strftime('%b %Y') for m in months]
    stock_in_by_month = [StockEntry.objects.filter(entry_type='in', timestamp__year=m.year, timestamp__month=m.month).aggregate(total=Sum('quantity'))['total'] or 0 for m in months]
    stock_out_by_month = [StockEntry.objects.filter(entry_type='out', timestamp__year=m.year, timestamp__month=m.month).aggregate(total=Sum('quantity'))['total'] or 0 for m in months]
    category_breakdown = list(Category.objects.annotate(product_count=Count('products')).values('name', 'product_count').order_by('-product_count'))
    rental_status_breakdown = list(Rental.objects.values('status').annotate(count=Count('id')))
    rental_product_breakdown = list(Rental.objects.values('product__name').annotate(count=Count('id')).order_by('-count')[:10])
    alert_type_breakdown = list(Alert.objects.values('alert_type').annotate(count=Count('id')))
    alert_product_breakdown = list(Alert.objects.values('product__name').annotate(count=Count('id')).order_by('-count')[:10])
    # Prepare dataframes
    dfs = {
        'Products by Category': pd.DataFrame(category_breakdown),
        'Stock In-Out by Month': pd.DataFrame({
            'Month': month_labels,
            'Stock In': stock_in_by_month,
            'Stock Out': stock_out_by_month,
        }),
        'Rentals by Status': pd.DataFrame(rental_status_breakdown),
        'Rentals by Product': pd.DataFrame(rental_product_breakdown),
        'Alerts by Type': pd.DataFrame(alert_type_breakdown),
        'Alerts by Product': pd.DataFrame(alert_product_breakdown),
    }
    def sanitize_sheetname(name):
        return name.replace('/', '-').replace('\\', '-').replace('?', '').replace('*', '').replace('[', '').replace(']', '').replace(':', '')
    if format == 'excel':
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for sheet, df in dfs.items():
                safe_sheet = sanitize_sheetname(sheet)
                df.to_excel(writer, sheet_name=safe_sheet, index=False)
        output.seek(0)
        response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="statistics_report.xlsx"'
        return response
    elif format == 'csv':
        output = BytesIO()
        # Combine all tables into one CSV with section headers
        for sheet, df in dfs.items():
            output.write(f'\n--- {sheet} ---\n'.encode())
            df.to_csv(output, index=False)
        output.seek(0)
        response = HttpResponse(output.read(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="statistics_report.csv"'
        return response
    elif format == 'pdf':
        # Render a simple HTML and use xhtml2pdf or similar for PDF
        try:
            from xhtml2pdf import pisa
        except ImportError:
            return HttpResponse('PDF export requires xhtml2pdf. Please install it.', status=500)
        html = render_to_string('reports/statistics_export_pdf.html', {
            'category_breakdown': category_breakdown,
            'month_labels': month_labels,
            'stock_in_by_month': stock_in_by_month,
            'stock_out_by_month': stock_out_by_month,
            'rental_status_breakdown': rental_status_breakdown,
            'rental_product_breakdown': rental_product_breakdown,
            'alert_type_breakdown': alert_type_breakdown,
            'alert_product_breakdown': alert_product_breakdown,
        })
        result = BytesIO()
        pisa.CreatePDF(html, dest=result)
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="statistics_report.pdf"'
        return response
    else:
        return HttpResponse('Invalid export format.', status=400)
