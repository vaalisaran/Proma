from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import models
from .models import InventoryAdjustment, SerialNumber, QuantityLimit, Alert, Rental, InventoryNotification, InventoryUser
from .serializers import InventoryAdjustmentSerializer, SerialNumberSerializer, QuantityLimitSerializer, AlertSerializer
from products.models import Product
from audit.models import AuditLog
from django.contrib import messages
from django.db import models
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from rest_framework import filters
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from tasks.decorators import admin_required
from django.utils.decorators import method_decorator
from django.conf import settings
from django.http import HttpResponseRedirect
from stock.models import StockEntry
from django.db.models import Sum
import csv
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from inventory.notifications import notify_inventory_admins

def _inventory_permission_redirect(request, access_field=None, manage_field=None):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    if request.user.is_admin:
        return None
    if access_field and not getattr(request.user, access_field, True):
        messages.error(request, 'You do not have access to this inventory page.')
        return redirect('dashboard-page')
    if request.method == 'POST' and manage_field and not getattr(request.user, manage_field, True):
        messages.error(request, 'You do not have permission to manage actions on this page.')
        return redirect('dashboard-page')
    return None

# Model for storing global standard limit (if not present, will add to models.py)
# class StandardLimit(models.Model):
#     value = models.PositiveIntegerField(default=1)
#     updated_at = models.DateTimeField(auto_now=True)

# View to handle setting the standard limit
def set_standard_limit(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    if request.method == 'POST':
        limit = request.POST.get('standard_limit')
        if limit and limit.isdigit():
            from .models import StandardLimit, Product, QuantityLimit
            obj, created = StandardLimit.objects.get_or_create(id=1, defaults={'value': int(limit)})
            if not created:
                obj.value = int(limit)
                obj.save()
            # Apply standard limit to all products without a QuantityLimit
            products_without_limit = Product.objects.filter(quantity_limit__isnull=True)
            for product in products_without_limit:
                QuantityLimit.objects.create(
                    product=product,
                    limit_quantity=int(limit),
                    is_active=True,
                    created_by=request.user
                )
            messages.success(request, f'Standard limit set to {limit}. Applied to {products_without_limit.count()} products without specific limits.')
        else:
            messages.error(request, 'Please enter a valid limit.')
    return redirect('inventory-limits-page')

@method_decorator(admin_required, name='dispatch')
class InventoryAdjustmentPageView(View):
    def get(self, request):
        permission_redirect = _inventory_permission_redirect(request, 'can_access_adjustments_page')
        if permission_redirect:
            return permission_redirect
        adjustments = InventoryAdjustment.objects.all().order_by('-timestamp')
        products = Product.objects.all()
        # Pagination: 50 per page
        paginator = Paginator(adjustments, 50)
        page_number = request.GET.get('page')
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        return render(request, 'inventory/adjustments.html', {'adjustments': page_obj.object_list, 'page_obj': page_obj, 'products': products})

    def post(self, request):
        permission_redirect = _inventory_permission_redirect(request, 'can_access_adjustments_page', 'can_manage_adjustments')
        if permission_redirect:
            return permission_redirect
        product_id = request.POST.get('product')
        adjustment_type = request.POST.get('adjustment_type')
        quantity = request.POST.get('quantity')
        reason = request.POST.get('reason')
        product = Product.objects.get(id=product_id)
        adj = InventoryAdjustment.objects.create(
            product=product,
            adjustment_type=adjustment_type,
            quantity=quantity,
            reason=reason,
            created_by=request.user
        )
        AuditLog.log(request.user, f'adjustment {adjustment_type}', adj)
        if not request.user.is_admin:
            notify_inventory_admins(
                request.user,
                'inventory_action',
                f'Inventory adjustment by {request.user.username}',
                f'{request.user.username} created a {adjustment_type} adjustment of {quantity} for {product.name}.',
                target_url='/inventory/adjustments/',
            )
        return redirect('inventory-adjustments-page')

class SerialNumbersPageView(View):
    def get(self, request):
        permission_redirect = _inventory_permission_redirect(request, 'can_access_serials_page')
        if permission_redirect:
            return permission_redirect
        search_query = request.GET.get('search', '')
        serials = SerialNumber.objects.all().select_related('product')
        if search_query:
            serials = serials.filter(
                models.Q(serial_number__icontains=search_query) |
                models.Q(product__name__icontains=search_query) |
                models.Q(product__brand__icontains=search_query) |
                models.Q(product__sku__icontains=search_query)
            )
        serials = serials.order_by('-created_at')
        paginator = Paginator(serials, 50)
        page_number = request.GET.get('page')
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        products_with_serials = Product.objects.exclude(serial_number__isnull=True).exclude(serial_number='')
        return render(request, 'inventory/serials.html', {
            'serials': page_obj.object_list,
            'page_obj': page_obj,
            'products_with_serials': products_with_serials,
            'search_query': search_query,
        })

    def post(self, request):
        permission_redirect = _inventory_permission_redirect(request, 'can_access_serials_page', 'can_manage_serials')
        if permission_redirect:
            return permission_redirect
        # SYNC LOGIC: Copy serial numbers from products to SerialNumber model
        products_with_serials = Product.objects.exclude(serial_number__isnull=True).exclude(serial_number='')
        created_count = 0
        updated_count = 0
        for product in products_with_serials:
            existing_serial = SerialNumber.objects.filter(serial_number=product.serial_number).first()
            if existing_serial:
                if existing_serial.product != product:
                    existing_serial.product = product
                    existing_serial.save()
                    updated_count += 1
            else:
                SerialNumber.objects.create(
                    serial_number=product.serial_number,
                    product=product,
                    status='available'
                )
                created_count += 1
        messages.success(request, f"Serial numbers synced! Created: {created_count}, Updated: {updated_count}")
        if not request.user.is_admin and (created_count or updated_count):
            notify_inventory_admins(
                request.user,
                'inventory_action',
                f'Serial sync by {request.user.username}',
                f'{request.user.username} synced serials. Created: {created_count}, Updated: {updated_count}.',
                target_url='/inventory/serials/',
            )
        return redirect('inventory-serials-page')

# Update QuantityLimitsPageView to pass standard_limit
@method_decorator(admin_required, name='dispatch')
class QuantityLimitsPageView(View):
    def get(self, request):
        permission_redirect = _inventory_permission_redirect(request, 'can_access_limits_page')
        if permission_redirect:
            return permission_redirect
        limits = QuantityLimit.objects.all()
        products = Product.objects.all().values('id', 'name', 'serial_number')
        products_list = list(products)
        from .models import StandardLimit
        try:
            standard_limit = StandardLimit.objects.get(id=1).value
        except StandardLimit.DoesNotExist:
            standard_limit = None
        return render(request, 'inventory/limits.html', {'limits': limits, 'products': products_list, 'standard_limit': standard_limit})

    def post(self, request):
        permission_redirect = _inventory_permission_redirect(request, 'can_access_limits_page', 'can_manage_limits')
        if permission_redirect:
            return permission_redirect
        product_id = request.POST.get('product')
        limit_quantity = request.POST.get('limit_quantity')
        is_active = request.POST.get('is_active') == 'on'
        
        product = Product.objects.get(id=product_id)
        limit, created = QuantityLimit.objects.update_or_create(
            product=product,
            defaults={
                'limit_quantity': limit_quantity,
                'is_active': is_active,
                'created_by': request.user
            }
        )
        
        if created:
            messages.success(request, f'Quantity limit set for {product.name}')
        else:
            messages.success(request, f'Quantity limit updated for {product.name}')
        if not request.user.is_admin:
            notify_inventory_admins(
                request.user,
                'inventory_action',
                f'Quantity limit update by {request.user.username}',
                f'{request.user.username} set limit {limit_quantity} for {product.name}. Active: {is_active}.',
                target_url='/inventory/limits/',
            )
        
        return redirect('inventory-limits-page')

class AlertsPageView(View):
    def get(self, request):
        permission_redirect = _inventory_permission_redirect(request, 'can_access_alerts_page')
        if permission_redirect:
            return permission_redirect
        alerts = Alert.objects.all().order_by('-created_at')
        # Pagination: 50 per page
        paginator = Paginator(alerts, 50)
        page_number = request.GET.get('page')
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        return render(request, 'inventory/alerts.html', {'alerts': page_obj.object_list, 'page_obj': page_obj})

    def post(self, request):
        permission_redirect = _inventory_permission_redirect(request, 'can_access_alerts_page', 'can_manage_alerts')
        if permission_redirect:
            return permission_redirect
        alert_id = request.POST.get('alert_id')
        action = request.POST.get('action')
        alert = get_object_or_404(Alert, id=alert_id)
        if action == 'acknowledge':
            alert.status = 'acknowledged'
            alert.acknowledged_at = timezone.now()
            alert.acknowledged_by = request.user
            alert.save()
            messages.success(request, 'Alert acknowledged')
        elif action == 'resolve':
            alert.status = 'resolved'
            alert.resolved_at = timezone.now()
            alert.resolved_by = request.user
            alert.save()
            messages.success(request, 'Alert resolved')
        if not request.user.is_admin:
            notify_inventory_admins(
                request.user,
                'inventory_action',
                f'Alert action by {request.user.username}',
                f'{request.user.username} performed "{action}" on alert #{alert.id} for {alert.product.name}.',
                target_url='/inventory/alerts/',
            )
        return redirect('inventory-alerts-page')


class InventoryNotificationsPageView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        notifications = InventoryNotification.objects.filter(recipient=request.user)
        status_filter = request.GET.get('status', '')
        type_filter = request.GET.get('type', '')
        date_filter = request.GET.get('date', '')
        search = request.GET.get('search', '')
        if status_filter == 'unread':
            notifications = notifications.filter(is_read=False)
        elif status_filter == 'read':
            notifications = notifications.filter(is_read=True)
        if type_filter:
            notifications = notifications.filter(notification_type=type_filter)
        if date_filter:
            notifications = notifications.filter(created_at__date=date_filter)
        if search:
            notifications = notifications.filter(
                Q(title__icontains=search) | Q(message__icontains=search)
            )
        paginator = Paginator(notifications, 30)
        page_number = request.GET.get('page')
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        return render(request, 'inventory/notifications.html', {
            'notifications': page_obj.object_list,
            'page_obj': page_obj,
            'status_filter': status_filter,
            'type_filter': type_filter,
            'date_filter': date_filter,
            'search': search,
            'type_choices': InventoryNotification.NOTIFICATION_TYPE_CHOICES,
        })

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        notification_id = request.POST.get('notification_id')
        action = request.POST.get('action')
        if action == 'mark_all_read':
            InventoryNotification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
            messages.success(request, 'All notifications marked as read.')
        elif notification_id:
            notification = get_object_or_404(InventoryNotification, id=notification_id, recipient=request.user)
            notification.is_read = True
            notification.save(update_fields=['is_read'])
            messages.success(request, 'Notification marked as read.')
        return redirect('inventory-notifications-page')

# API Views
class InventoryAdjustmentAPI(ListCreateAPIView):
    queryset = InventoryAdjustment.objects.all()
    serializer_class = InventoryAdjustmentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class SerialNumberPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100

class SerialNumbersAPI(ListCreateAPIView):
    queryset = SerialNumber.objects.all()
    serializer_class = SerialNumberSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['serial_number', 'product__name', 'product__brand', 'product__sku']
    pagination_class = SerialNumberPagination

class QuantityLimitsAPI(ListCreateAPIView):
    queryset = QuantityLimit.objects.all()
    serializer_class = QuantityLimitSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class QuantityLimitDetailAPI(RetrieveUpdateDestroyAPIView):
    queryset = QuantityLimit.objects.all()
    serializer_class = QuantityLimitSerializer
    permission_classes = [IsAuthenticated]

class AlertsAPI(ListCreateAPIView):
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

class AlertDetailAPI(RetrieveUpdateDestroyAPIView):
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

class AcknowledgeAlertAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, alert_id):
        try:
            alert = Alert.objects.get(id=alert_id)
            alert.status = 'acknowledged'
            alert.acknowledged_at = timezone.now()
            alert.acknowledged_by = request.user
            alert.save()
            return Response({'status': 'success', 'message': 'Alert acknowledged'})
        except Alert.DoesNotExist:
            return Response({'status': 'error', 'message': 'Alert not found'}, status=status.HTTP_404_NOT_FOUND)

class ResolveAlertAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, alert_id):
        try:
            alert = Alert.objects.get(id=alert_id)
            alert.status = 'resolved'
            alert.resolved_at = timezone.now()
            alert.resolved_by = request.user
            alert.save()
            return Response({'status': 'success', 'message': 'Alert resolved'})
        except Alert.DoesNotExist:
            return Response({'status': 'error', 'message': 'Alert not found'}, status=status.HTTP_404_NOT_FOUND)

class RentalManagementView(View):
    def get(self, request):
        permission_redirect = _inventory_permission_redirect(request, 'can_access_rentals_page')
        if permission_redirect:
            return permission_redirect
        rentals = Rental.objects.select_related('product').order_by('-created_at')
        overdue_rentals = rentals.filter(status='active', return_date__lt=timezone.now().date())
        products = Product.objects.all()
        # Calculate available quantity for each product
        product_availability = {}
        for product in products:
            from stock.models import StockEntry
            stock_in = StockEntry.objects.filter(product=product, entry_type='in').aggregate(total=models.Sum('quantity'))['total'] or 0
            stock_out = StockEntry.objects.filter(product=product, entry_type='out').aggregate(total=models.Sum('quantity'))['total'] or 0
            available = stock_in - stock_out
            product.stock_in = stock_in
            product.stock_out = stock_out
            product.available = available
            product_availability[product.id] = available
        products = [p for p in products if p.available > 0]
        return render(request, 'inventory/rentals.html', {
            'rentals': rentals,
            'overdue_rentals': overdue_rentals,
            'products': products,
            'product_availability': product_availability,
        })

    def post(self, request):
        permission_redirect = _inventory_permission_redirect(request, 'can_access_rentals_page', 'can_manage_rentals')
        if permission_redirect:
            return permission_redirect
        action = request.POST.get('action')
        if action == 'create':
            product_id = request.POST.get('product')
            quantity = int(request.POST.get('quantity'))
            rented_to = request.POST.get('rented_to')
            reason = request.POST.get('reason')
            rental_date = request.POST.get('rental_date')
            rental_time = request.POST.get('rental_time')
            return_date = request.POST.get('return_date') or None
            product = Product.objects.get(id=product_id)
            # Check available quantity
            from stock.models import StockEntry
            stock_in = StockEntry.objects.filter(product=product, entry_type='in').aggregate(total=models.Sum('quantity'))['total'] or 0
            stock_out = StockEntry.objects.filter(product=product, entry_type='out').aggregate(total=models.Sum('quantity'))['total'] or 0
            available_quantity = stock_in - stock_out
            if quantity > available_quantity:
                messages.error(request, f'Cannot rent {quantity} units of {product.name}. Only {available_quantity} available in stock.')
                return redirect('rental-management')
            # Reduce product quantity
            StockEntry.objects.create(product=product, quantity=quantity, entry_type='out', created_by=request.user, description='Rental')
            Rental.objects.create(
                product=product,
                quantity=quantity,
                rented_to=rented_to,
                reason=reason,
                rental_date=rental_date,
                rental_time=rental_time,
                return_date=return_date,
                status='active',
                created_by=request.user
            )
            messages.success(request, f'Rented {quantity} of {product.name} to {rented_to}.')
            if not request.user.is_admin:
                notify_inventory_admins(
                    request.user,
                    'inventory_action',
                    f'Rental created by {request.user.username}',
                    f'{request.user.username} rented {quantity} unit(s) of {product.name} to {rented_to}.',
                    target_url='/inventory/rentals/',
                )
        elif action == 'return':
            rental_id = request.POST.get('rental_id')
            rental = Rental.objects.get(id=rental_id)
            if rental.status == 'active':
                # Restore product quantity
                from stock.models import StockEntry
                StockEntry.objects.create(product=rental.product, quantity=rental.quantity, entry_type='in', created_by=request.user, description='Rental Return')
                rental.status = 'returned'
                rental.save()
                messages.success(request, f'Rental for {rental.product.name} marked as returned.')
                if not request.user.is_admin:
                    notify_inventory_admins(
                        request.user,
                        'inventory_action',
                        f'Rental returned by {request.user.username}',
                        f'{request.user.username} marked rental #{rental.id} for {rental.product.name} as returned.',
                        target_url='/inventory/rentals/',
                    )
        return redirect('rental-management')

def inventory_shortage_view(request):
    permission_redirect = _inventory_permission_redirect(request, 'can_access_shortage_page')
    if permission_redirect:
        return permission_redirect
    from .models import Product, QuantityLimit, StandardLimit
    # Get all products
    products = Product.objects.all()
    products_list = [{'id': p.id, 'name': p.name} for p in products]
    # Get standard limit if exists
    try:
        standard_limit = StandardLimit.objects.get(id=1).value
    except StandardLimit.DoesNotExist:
        standard_limit = None
    shortage_items = []
    for product in products:
        # Calculate current stock
        stock_in = StockEntry.objects.filter(product=product, entry_type='in').aggregate(total=Sum('quantity'))['total'] or 0
        stock_out = StockEntry.objects.filter(product=product, entry_type='out').aggregate(total=Sum('quantity'))['total'] or 0
        current_quantity = stock_in - stock_out
        # Determine limit (priority: specific > standard)
        try:
            limit_obj = QuantityLimit.objects.get(product=product, is_active=True)
            limit = limit_obj.limit_quantity
        except QuantityLimit.DoesNotExist:
            limit = standard_limit
        if limit is not None and current_quantity <= limit:
            qty_to_buy = abs(limit - current_quantity)
            shortage_items.append({
                'product': {'id': product.id, 'name': product.name},
                'current_quantity': current_quantity,
                'limit': limit,
                'qty_to_buy': qty_to_buy
            })
    return render(request, 'inventory/shortage.html', {'shortage_items': shortage_items, 'products': products_list})

def inventory_shortage_export_csv(request):
    permission_redirect = _inventory_permission_redirect(request, 'can_access_shortage_page')
    if permission_redirect:
        return permission_redirect
    if not request.user.is_admin and not getattr(request.user, 'can_manage_shortage_exports', True):
        messages.error(request, 'You do not have permission to export shortage data.')
        return redirect('inventory-shortage-page')
    from .models import Product, QuantityLimit, StandardLimit
    from stock.models import StockEntry
    from django.db.models import Sum
    # Get all products
    products = Product.objects.all()
    # Get standard limit if exists
    try:
        standard_limit = StandardLimit.objects.get(id=1).value
    except StandardLimit.DoesNotExist:
        standard_limit = None
    shortage_items = []
    for product in products:
        stock_in = StockEntry.objects.filter(product=product, entry_type='in').aggregate(total=Sum('quantity'))['total'] or 0
        stock_out = StockEntry.objects.filter(product=product, entry_type='out').aggregate(total=Sum('quantity'))['total'] or 0
        current_quantity = stock_in - stock_out
        try:
            limit_obj = QuantityLimit.objects.get(product=product, is_active=True)
            limit = limit_obj.limit_quantity
        except QuantityLimit.DoesNotExist:
            limit = standard_limit
        if limit is not None and current_quantity <= limit:
            qty_to_buy = abs(limit - current_quantity)
            shortage_items.append({
                'product': {'id': product.id, 'name': product.name},
                'current_quantity': current_quantity,
                'limit': limit,
                'qty_to_buy': qty_to_buy
            })
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory_shortage.csv"'
    writer = csv.writer(response)
    writer.writerow(['Product', 'In Quantity', 'Qty to Buy', 'Buyed Qty', 'Check'])
    for item in shortage_items:
        writer.writerow([
            item['product']['name'],
            item['current_quantity'],
            item['qty_to_buy'],
            '',  # Buyed Qty
            ''   # Check
        ])
    return response

def inventory_shortage_export_pdf(request):
    permission_redirect = _inventory_permission_redirect(request, 'can_access_shortage_page')
    if permission_redirect:
        return permission_redirect
    if not request.user.is_admin and not getattr(request.user, 'can_manage_shortage_exports', True):
        messages.error(request, 'You do not have permission to export shortage data.')
        return redirect('inventory-shortage-page')
    from .models import Product, QuantityLimit, StandardLimit
    from stock.models import StockEntry
    from django.db.models import Sum
    # Get all products
    products = Product.objects.all()
    # Get standard limit if exists
    try:
        standard_limit = StandardLimit.objects.get(id=1).value
    except StandardLimit.DoesNotExist:
        standard_limit = None
    shortage_items = []
    for product in products:
        stock_in = StockEntry.objects.filter(product=product, entry_type='in').aggregate(total=Sum('quantity'))['total'] or 0
        stock_out = StockEntry.objects.filter(product=product, entry_type='out').aggregate(total=Sum('quantity'))['total'] or 0
        current_quantity = stock_in - stock_out
        try:
            limit_obj = QuantityLimit.objects.get(product=product, is_active=True)
            limit = limit_obj.limit_quantity
        except QuantityLimit.DoesNotExist:
            limit = standard_limit
        if limit is not None and current_quantity <= limit:
            qty_to_buy = abs(limit - current_quantity)
            shortage_items.append({
                'product': {'id': product.id, 'name': product.name},
                'current_quantity': current_quantity,
                'limit': limit,
                'qty_to_buy': qty_to_buy
            })
    html = render_to_string('inventory/shortage_pdf.html', {'shortage_items': shortage_items})
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="inventory_shortage.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response
