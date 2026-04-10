from django.shortcuts import render, redirect
from django.views import View
from .models import AuditLog
from inventory.models import InventoryUser
from django.db.models import Q
from functools import reduce
from operator import or_
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse
import pandas as pd
from datetime import datetime
from urllib.parse import urlencode
from fpdf import FPDF
from tasks.decorators import admin_required
from django.utils.decorators import method_decorator
# PDF export will be added later

@method_decorator(admin_required, name='dispatch')
class AuditLogPageView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        logs = AuditLog.objects.all().order_by('-timestamp')
        users = InventoryUser.objects.all().order_by('username')

        # Filters
        user_id = request.GET.get('user')
        year = request.GET.get('year')
        month = request.GET.get('month')
        date = request.GET.get('date')
        search = request.GET.get('search')
        export = request.GET.get('export')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        action_filter = request.GET.get('action', '').strip()
        model_filter = request.GET.get('model', '').strip()

        # ANY-match filtering: if multiple inputs are provided, match logs that satisfy
        # at least one of them (OR), so even a single parameter is enough.
        filter_clauses = []
        if user_id and str(user_id).isdigit():
            filter_clauses.append(Q(user_id=user_id))
        if year and str(year).isdigit():
            filter_clauses.append(Q(timestamp__year=year))
        if month and str(month).isdigit():
            filter_clauses.append(Q(timestamp__month=month))
        if date:
            filter_clauses.append(Q(timestamp__date=date))
        if start_date and end_date:
            filter_clauses.append(Q(timestamp__date__range=[start_date, end_date]))
        elif start_date:
            filter_clauses.append(Q(timestamp__date__gte=start_date))
        elif end_date:
            filter_clauses.append(Q(timestamp__date__lte=end_date))
        if search:
            filter_clauses.append(
                Q(action__icontains=search) |
                Q(model_name__icontains=search) |
                Q(object_id__icontains=search) |
                Q(changes__icontains=search) |
                Q(user__username__icontains=search)
            )
        if action_filter:
            filter_clauses.append(Q(action__icontains=action_filter))
        if model_filter:
            filter_clauses.append(Q(model_name__icontains=model_filter))

        if filter_clauses:
            logs = logs.filter(reduce(or_, filter_clauses))

        # Export Excel
        if export == 'excel':
            df = pd.DataFrame(list(logs.values('user__username', 'action', 'model_name', 'object_id', 'timestamp', 'changes')))
            df.rename(columns={
                'user__username': 'User',
                'action': 'Action',
                'model_name': 'Model',
                'object_id': 'Object ID',
                'timestamp': 'Timestamp',
                'changes': 'Changes',
            }, inplace=True)
            # Convert all timestamps to string to avoid timezone issues
            if not df.empty and 'Timestamp' in df.columns:
                df['Timestamp'] = df['Timestamp'].apply(lambda x: x.isoformat(sep=' ', timespec='minutes') if pd.notnull(x) else '')
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename=audit_logs.xlsx'
            with pd.ExcelWriter(response, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Audit Logs')
            return response

        # Export PDF
        if export == 'pdf':
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, 'Audit Logs', ln=True, align='C')
            pdf.ln(5)
            pdf.set_font('Arial', 'B', 10)
            # Table header
            headers = ['User', 'Action', 'Model', 'Object ID', 'Timestamp', 'Changes']
            col_widths = [30, 20, 25, 20, 40, 55]
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 8, header, border=1)
            pdf.ln()
            pdf.set_font('Arial', '', 9)
            for log in logs[:200]:  # Limit to 200 rows for PDF
                row = [
                    str(log.user) if log.user else 'System',
                    log.action,
                    log.model_name,
                    str(log.object_id),
                    log.timestamp.strftime('%Y-%m-%d %H:%M'),
                    (log.changes[:40] + '...') if log.changes and len(log.changes) > 40 else (log.changes or '-')
                ]
                for i, cell in enumerate(row):
                    pdf.cell(col_widths[i], 8, cell, border=1)
                pdf.ln()
            response = HttpResponse(pdf.output(dest='S').encode('latin1'), content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=audit_logs.pdf'
            return response

        # Pagination
        paginator = Paginator(logs, 50)
        page_number = request.GET.get('page')
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        # Years for filter dropdown
        years = AuditLog.objects.dates('timestamp', 'year', order='DESC')
        months = range(1, 13)
        query_params = request.GET.copy()
        query_params.pop('page', None)
        query_params.pop('export', None)
        preserved_query = urlencode(query_params, doseq=True)

        context = {
            'logs': page_obj.object_list,
            'page_obj': page_obj,
            'users': users,
            'years': years,
            'months': months,
            'selected_user': user_id,
            'selected_year': year,
            'selected_month': month,
            'selected_date': date,
            'search': search,
            'start_date': start_date,
            'end_date': end_date,
            'action_filter': action_filter,
            'model_filter': model_filter,
            'preserved_query': preserved_query,
        }
        return render(request, 'audit/logs.html', context)
