from django.shortcuts import render, redirect
from django.views import View
from .models import AuditLog
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse
import pandas as pd
from datetime import datetime
from fpdf import FPDF
from users.views import admin_required
from django.utils.decorators import method_decorator
# PDF export will be added later

User = get_user_model()

@method_decorator(admin_required, name='dispatch')
class AuditLogPageView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
        logs = AuditLog.objects.all().order_by('-timestamp')
        users = User.objects.all()

        # Filters
        user_id = request.GET.get('user')
        year = request.GET.get('year')
        month = request.GET.get('month')
        date = request.GET.get('date')
        search = request.GET.get('search')
        export = request.GET.get('export')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        if user_id:
            logs = logs.filter(user_id=user_id)
        if year:
            logs = logs.filter(timestamp__year=year)
        if month:
            logs = logs.filter(timestamp__month=month)
        if date:
            logs = logs.filter(timestamp__date=date)
        if start_date and end_date:
            logs = logs.filter(timestamp__date__range=[start_date, end_date])
        if search:
            logs = logs.filter(
                Q(action__icontains=search) |
                Q(model_name__icontains=search) |
                Q(object_id__icontains=search) |
                Q(changes__icontains=search) |
                Q(user__username__icontains=search)
            )

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
        }
        return render(request, 'audit/logs.html', context)
