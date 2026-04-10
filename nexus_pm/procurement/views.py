from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from products.models import Product
from stock.models import StockEntry
from django.db.models import Sum
import openpyxl
from inventory.models import Alert
from django.contrib.auth import get_user_model
User = get_user_model()

class ProcurementUploadView(View):
    def get(self, request):
        products = Product.objects.all()
        return render(request, 'procurement/upload.html', {'products': products})

    def post(self, request):
        results = []
        insufficient_count = 0
        products = {p.name.lower(): p for p in Product.objects.all()}
        
        # Helper to process single row
        def process_request(product_name, requested_qty):
            nonlocal insufficient_count
            product = products.get(str(product_name).strip().lower())
            
            try:
                rq_qty = float(requested_qty)
            except (ValueError, TypeError):
                rq_qty = 0
                
            if not product or rq_qty <= 0:
                results.append({
                    'product_name': product_name,
                    'requested_qty': requested_qty,
                    'current_stock': '-',
                    'status': 'invalid',
                    'product_id': None,
                    'rack_number': '',
                    'shelf_number': '',
                    'alert': False,
                })
                return
                
            stock_in = StockEntry.objects.filter(product=product, entry_type='in').aggregate(total=Sum('quantity'))['total'] or 0
            stock_out = StockEntry.objects.filter(product=product, entry_type='out').aggregate(total=Sum('quantity'))['total'] or 0
            current_stock = stock_in - stock_out
            
            if current_stock <= 0:
                status = 'out_of_stock'
                alert = True
                insufficient_count += 1
            elif current_stock < rq_qty:
                status = 'insufficient'
                alert = True
                insufficient_count += 1
            else:
                status = 'ok'
                alert = False
                
            results.append({
                'product_name': product.name,
                'requested_qty': int(rq_qty),
                'current_stock': current_stock,
                'status': status,
                'product_id': product.id,
                'rack_number': product.rack_number or '',
                'shelf_number': product.shelf_number or '',
                'alert': alert,
            })

        if 'excel_file' in request.FILES:
            excel_file = request.FILES['excel_file']
            wb = openpyxl.load_workbook(excel_file)
            ws = wb.active
            header = [cell.value for cell in ws[1]]
            name_idx = header.index('Product Name')
            qty_idx = header.index('Requested Quantity')
            for row in ws.iter_rows(min_row=2, values_only=True):
                process_request(row[name_idx], row[qty_idx])
        elif request.POST.get('form_type') == 'manual':
            process_request(request.POST.get('product_name'), request.POST.get('requested_qty'))
            
        if insufficient_count > 0:
            messages.warning(request, f'There are {insufficient_count} items with insufficient or zero stock. Please review the report below.')
        
        return render(request, 'procurement/upload.html', {'results': results, 'products': Product.objects.all()})

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.http import JsonResponse

@method_decorator(csrf_exempt, name='dispatch')
class ProcurementRestockView(View):
    def post(self, request):
        product_id = request.POST.get('product_id')
        requested_qty = request.POST.get('requested_qty') or request.POST.get('restock_qty')
        if not product_id or not requested_qty:
            messages.error(request, 'Invalid product or quantity.')
            return redirect('procurement-upload')
        try:
            product = Product.objects.get(id=product_id)
            requested_qty = int(requested_qty)
            stock_in = StockEntry.objects.filter(product=product, entry_type='in').aggregate(total=Sum('quantity'))['total'] or 0
            stock_out = StockEntry.objects.filter(product=product, entry_type='out').aggregate(total=Sum('quantity'))['total'] or 0
            current_stock = stock_in - stock_out
            if requested_qty > current_stock:
                # Create alert
                Alert.objects.create(
                    product=product,
                    alert_type='low_stock' if current_stock > 0 else 'out_of_stock',
                    status='active',
                    message=f'Requested {requested_qty}, but only {current_stock} in stock.',
                    current_quantity=current_stock,
                    limit_quantity=requested_qty,
                )
                messages.warning(request, f'Alert sent: Requested {requested_qty}, but only {current_stock} in stock for {product.name}.')
            else:
                messages.success(request, 'Restock request submitted!')
        except Product.DoesNotExist:
            messages.error(request, 'Product not found.')
        return redirect('procurement-upload')

# Send All Alerts View
@csrf_exempt
@require_POST
def send_all_alerts(request):
    import json
    data = json.loads(request.body.decode('utf-8'))
    product_alerts = data.get('alerts', [])
    alert_count = 0
    for item in product_alerts:
        product_id = item.get('product_id')
        requested_qty = item.get('requested_qty')
        current_stock = item.get('current_stock')
        if not product_id or not requested_qty:
            continue
        try:
            product = Product.objects.get(id=product_id)
            Alert.objects.create(
                product=product,
                alert_type='low_stock' if current_stock > 0 else 'out_of_stock',
                status='active',
                message=f'Requested {requested_qty}, but only {current_stock} in stock.',
                current_quantity=current_stock,
                limit_quantity=requested_qty,
            )
            alert_count += 1
        except Product.DoesNotExist:
            continue
    return JsonResponse({'status': 'success', 'alert_count': alert_count}) 

from django.http import HttpResponse
from openpyxl.styles import Font, PatternFill, Alignment

class DownloadProcurementTemplateView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
            
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Procurement Template"
        
        headers = ['Product Name', 'Requested Quantity']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            cell.alignment = Alignment(horizontal="center")
            
        sample_data = ['Sample Product', 50]
        for col, value in enumerate(sample_data, 1):
            cell = ws.cell(row=2, column=col, value=value)
            
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 20
        
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="procurement_template.xlsx"'
        wb.save(response)
        return response