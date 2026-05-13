from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Sum, Q, Min, Max
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import FileResponse

from .models import (
    Invoice, OtherIncome, Salary, OtherExpense, ProjectDomain, ProjectServer, 
    Payment, ClientAdvance, Project, ProjectService, ProjectServiceTeam, ProjectTeam,
    ProjectExbot
)
from .pdf_utils import generate_income_statement_pdf, generate_cash_flow_statement_pdf, generate_balance_sheet_pdf

def get_financial_date_filter(request, date_field='date'):
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    month = request.query_params.get('month')
    year = request.query_params.get('year')
    filter_type = request.query_params.get('filter_type')

    q = Q()
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            q &= Q(**{f"{date_field}__range": [start, end]})
        except ValueError:
            pass
    elif month and year:
        try:
            q &= Q(**{f"{date_field}__year": int(year), f"{date_field}__month": int(month)})
        except ValueError:
            pass
    elif year:
        try:
            q &= Q(**{f"{date_field}__year": int(year)})
        except ValueError:
            pass
    elif filter_type:
        from .utils import get_date_filter_q
        filter_q = get_date_filter_q(filter_type, date_field)
        if isinstance(filter_q, tuple): # some error handling in get_date_filter_q
            q &= filter_q[0] if filter_q[0] else Q()
        else:
            q &= filter_q
            
    return q

class IncomeStatementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Revenue
        invoice_q = get_financial_date_filter(request, 'invoice_date')
        other_income_q = get_financial_date_filter(request, 'date')
        
        invoices = Invoice.objects.filter(invoice_q)
        other_incomes = OtherIncome.objects.filter(other_income_q)
        
        invoice_revenue = invoices.aggregate(total=Sum('total_amount'))['total'] or 0
        other_revenue = other_incomes.aggregate(total=Sum('amount'))['total'] or 0
        total_revenue = invoice_revenue + other_revenue

        # Expenses
        salary_q = get_financial_date_filter(request, 'start_date')
        expense_q = get_financial_date_filter(request, 'date')
        domain_q = get_financial_date_filter(request, 'purchase_date')
        
        salaries = Salary.objects.filter(salary_q)
        other_expenses = OtherExpense.objects.filter(expense_q)
        domains = ProjectDomain.objects.filter(domain_q)
        servers = ProjectServer.objects.filter(domain_q)

        salary_expense = sum([(s.basic + s.bonus - s.deductions) for s in salaries])
        other_expense_total = other_expenses.aggregate(total=Sum('amount'))['total'] or 0
        domain_expense = domains.aggregate(total=Sum('cost'))['total'] or 0
        server_expense = servers.aggregate(total=Sum('cost'))['total'] or 0
        
        total_expenses = salary_expense + other_expense_total + domain_expense + server_expense
        
        net_income = total_revenue - total_expenses
        
        data = {
            'revenue': {
                'invoices': invoice_revenue,
                'other_income': other_revenue,
                'total_revenue': total_revenue
            },
            'expenses': {
                'salaries': salary_expense,
                'other_expenses': other_expense_total,
                'domains_and_servers': domain_expense + server_expense,
                'total_expenses': total_expenses
            },
            'net_income': net_income
        }

        if request.query_params.get('export') == 'pdf':
            buffer = generate_income_statement_pdf(data, request.query_params)
            return FileResponse(buffer, as_attachment=True, filename='Income_Statement.pdf')
            
        return Response(data)

class CashFlowStatementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payment_q = get_financial_date_filter(request, 'payment_date')
        income_q = get_financial_date_filter(request, 'date')
        advance_q = get_financial_date_filter(request, 'created_at')

        # Cash In
        payments = Payment.objects.filter(payment_q).aggregate(total=Sum('amount'))['total'] or 0
        other_income = OtherIncome.objects.filter(income_q).aggregate(total=Sum('amount'))['total'] or 0
        advances = ClientAdvance.objects.filter(advance_q).aggregate(total=Sum('amount'))['total'] or 0
        
        total_cash_in = payments + other_income + advances

        # Cash Out
        expense_q = get_financial_date_filter(request, 'date')
        salary_q = get_financial_date_filter(request, 'start_date')
        domain_q = get_financial_date_filter(request, 'purchase_date')

        other_expenses = OtherExpense.objects.filter(expense_q).aggregate(total=Sum('amount'))['total'] or 0
        
        # Only Paid salaries in period
        salary_out = Salary.objects.filter(salary_q, status='Paid').aggregate(
            total=Sum(F('basic') + F('bonus') - F('deductions'))
        )['total'] or 0
        
        domains_paid = ProjectDomain.objects.filter(domain_q, payment_status='PAID').aggregate(total=Sum('cost'))['total'] or 0
        servers_paid = ProjectServer.objects.filter(domain_q, payment_status='PAID').aggregate(total=Sum('cost'))['total'] or 0
        
        total_cash_out = other_expenses + salary_out + domains_paid + servers_paid
        
        net_cash_flow = total_cash_in - total_cash_out

        data = {
            'cash_in': {
                'invoice_payments': payments,
                'other_income': other_income,
                'client_advances': advances,
                'total_cash_in': total_cash_in
            },
            'cash_out': {
                'salaries_paid': salary_out,
                'other_expenses': other_expenses,
                'domains_servers_paid': domains_paid + servers_paid,
                'total_cash_out': total_cash_out
            },
            'net_cash_flow': net_cash_flow
        }
        
        if request.query_params.get('export') == 'pdf':
            try:
                buffer = generate_cash_flow_statement_pdf(data, request.query_params)
                pdf_data = buffer.getvalue()
                response = HttpResponse(pdf_data, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="Cash_Flow_Statement.pdf"'
                response['Content-Length'] = len(pdf_data)
                response["Access-Control-Allow-Origin"] = "*"
                response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
                response["Access-Control-Allow-Headers"] = "*"
                return response
            except Exception as e:
                import traceback
                return Response({
                    "error": "PDF Generation Failed",
                    "details": str(e),
                    "traceback": traceback.format_exc()
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        return Response(data)

class BalanceSheetView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Balance sheet is typically a snapshot at a point in time. 
        # If an end_date is provided, we use it as the "as of" date.
        end_date_str = request.query_params.get('end_date')
        
        # Assets
        # 1. Cash (All-time Cash In - All-time Cash Out, up to end_date)
        # Simplified: Net Cash Flow up to Date
        cash_in_q = Q()
        cash_out_q = Q()

        invoice_q = Q()
        salary_q = Q()
        advance_q = Q()
        
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                cash_in_q &= Q(payment_date__date__lte=end_date)
                cash_out_q &= Q(date__lte=end_date)
                invoice_q &= Q(invoice_date__lte=end_date)
                salary_q &= Q(start_date__lte=end_date)
                advance_q &= Q(created_at__date__lte=end_date)
            except ValueError:
                pass

        # Cash Calculation (Simplified to use the cash flow logic but all-time/up-to-date)
        payments = Payment.objects.filter(cash_in_q).aggregate(total=Sum('amount'))['total'] or 0
        other_income = OtherIncome.objects.filter(cash_in_q).aggregate(total=Sum('amount'))['total'] or 0
        advances = ClientAdvance.objects.filter(advance_q).aggregate(total=Sum('amount'))['total'] or 0
        total_cash_in = payments + other_income + advances
        
        other_exp = OtherExpense.objects.filter(cash_out_q).aggregate(total=Sum('amount'))['total'] or 0
        # Salaries Paid up to date (Optimized for Server)
        sals_paid = Salary.objects.filter(salary_q, status='Paid').aggregate(
            total=Sum(F('basic') + F('bonus') - F('deductions'))
        )['total'] or 0
        
        domain_cost = ProjectDomain.objects.filter(payment_status='PAID').aggregate(total=Sum('cost'))['total'] or 0
        if end_date_str:
             domain_cost = ProjectDomain.objects.filter(purchase_date__lte=end_date, payment_status='PAID').aggregate(total=Sum('cost'))['total'] or 0
             
        server_cost = ProjectServer.objects.filter(payment_status='PAID').aggregate(total=Sum('cost'))['total'] or 0
        if end_date_str:
             server_cost = ProjectServer.objects.filter(purchase_date__lte=end_date, payment_status='PAID').aggregate(total=Sum('cost'))['total'] or 0

        total_cash_out = other_exp + sals_paid + domain_cost + server_cost
        cash_on_hand = total_cash_in - total_cash_out

        # Accounts Receivable (Balances due on Invoices up to date)
        accounts_receivable = Invoice.objects.filter(invoice_q).aggregate(total=Sum('balance_due'))['total'] or 0

        total_assets = cash_on_hand + accounts_receivable

        # Liabilities
        # Accounts Payable (Optimized for Server)
        unpaid_sals = Salary.objects.filter(salary_q).exclude(status='Paid').aggregate(
            total=Sum(F('basic') + F('bonus') - F('deductions'))
        )['total'] or 0
        
        unpaid_domains = ProjectDomain.objects.filter(payment_status='UNPAID').aggregate(total=Sum('cost'))['total'] or 0
        if end_date_str:
            unpaid_domains = ProjectDomain.objects.filter(purchase_date__lte=end_date, payment_status='UNPAID').aggregate(total=Sum('cost'))['total'] or 0
            
        unpaid_servers = ProjectServer.objects.filter(payment_status='UNPAID').aggregate(total=Sum('cost'))['total'] or 0
        if end_date_str:
            unpaid_servers = ProjectServer.objects.filter(purchase_date__lte=end_date, payment_status='UNPAID').aggregate(total=Sum('cost'))['total'] or 0
            
        accounts_payable = unpaid_sals + unpaid_domains + unpaid_servers

        # Unearned Revenue / Advances Remaining
        advances_remaining = ClientAdvance.objects.filter(advance_q).aggregate(total=Sum('remaining_amount'))['total'] or 0

        total_liabilities = accounts_payable + advances_remaining

        # Equity (Retained Earnings = Net Income all time up to date)
        invoice_rev = Invoice.objects.filter(invoice_q).aggregate(total=Sum('total_amount'))['total'] or 0
        total_rev = invoice_rev + other_income
        
        # Equity calculations (Optimized for Server)
        salary_exp = Salary.objects.filter(salary_q).aggregate(
            total=Sum(F('basic') + F('bonus') - F('deductions'))
        )['total'] or 0
        domain_exp = ProjectDomain.objects.filter().aggregate(total=Sum('cost'))['total'] or 0
        server_exp = ProjectServer.objects.filter().aggregate(total=Sum('cost'))['total'] or 0
        
        if end_date_str:
            domain_exp = ProjectDomain.objects.filter(purchase_date__lte=end_date).aggregate(total=Sum('cost'))['total'] or 0
            server_exp = ProjectServer.objects.filter(purchase_date__lte=end_date).aggregate(total=Sum('cost'))['total'] or 0
            
        total_exp = salary_exp + other_exp + domain_exp + server_exp
        
        retained_earnings = total_rev - total_exp
        total_equity = retained_earnings

        data = {
            'assets': {
                'cash_on_hand': cash_on_hand,
                'accounts_receivable': accounts_receivable,
                'total_assets': total_assets
            },
            'liabilities': {
                'accounts_payable': accounts_payable,
                'client_advances': advances_remaining,
                'total_liabilities': total_liabilities
            },
            'equity': {
                'retained_earnings': retained_earnings,
                'total_equity': total_equity
            }
        }
        
        if request.query_params.get('export') == 'pdf':
            try:
                buffer = generate_balance_sheet_pdf(data, request.query_params)
                pdf_data = buffer.getvalue()
                response = HttpResponse(pdf_data, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="Balance_Sheet.pdf"'
                response['Content-Length'] = len(pdf_data)
                # Manual CORS headers for stability
                response["Access-Control-Allow-Origin"] = "*"
                response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
                response["Access-Control-Allow-Headers"] = "*"
                return response
            except Exception as e:
                import traceback
                return Response({
                    "error": "PDF Generation Failed",
                    "details": str(e),
                    "traceback": traceback.format_exc()
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(data)

class ProjectAnalyticalAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _run_expiry_check(self):
        """
        Runs the domain & server expiry notification check.
        Called automatically whenever this API is triggered.
        Mirrors the logic in the check_expiries management command.
        """
        from .models import Notification, User, Role

        today = timezone.now().date()
        max_date = today + timedelta(days=30)

        # Find SuperAdmin users
        try:
            superadmin_role = Role.objects.get(name='SuperAdmin')
            superadmins = list(User.objects.filter(role=superadmin_role))
        except Role.DoesNotExist:
            superadmins = list(User.objects.filter(is_superuser=True))

        if not superadmins:
            return

        def create_notification_if_new(recipients, message, project=None, notification_type=None):
            for user in recipients:
                already_exists = Notification.objects.filter(
                    user=user,
                    message=message,
                    created_at__date=today
                ).exists()
                if not already_exists:
                    Notification.objects.create(
                        user=user,
                        message=message,
                        project=project,
                        notification_type=notification_type
                    )

        # Check Domains
        expiring_domains = ProjectDomain.objects.filter(
            expiration_date__gte=today,
            expiration_date__lte=max_date
        )
        for domain in expiring_domains:
            days_remaining = (domain.expiration_date - today).days
            message = (
                f"Domain Expiry Alert: The domain '{domain.name}' for project "
                f"'{domain.project.name if domain.project else 'N/A'}' is expiring on "
                f"{domain.expiration_date} ({days_remaining} days remaining). "
                f"Action Required: Please contact the provider '{domain.purchased_from or 'N/A'}' "
                f"to renew the domain."
            )
            create_notification_if_new(superadmins, message, project=domain.project, notification_type='domain_alert')

        # Check Servers
        expiring_servers = ProjectServer.objects.filter(
            expiration_date__gte=today,
            expiration_date__lte=max_date
        )
        for server in expiring_servers:
            days_remaining = (server.expiration_date - today).days
            message = (
                f"Server Expiry Alert: The server '{server.name}' ({server.server_type}) for project "
                f"'{server.project.name if server.project else 'N/A'}' is expiring on "
                f"{server.expiration_date} ({days_remaining} days remaining). "
                f"Action Required: Please ensure payment is processed or contact the provider "
                f"'{server.purchased_from or 'N/A'}' to avoid service interruption."
            )
            create_notification_if_new(superadmins, message, project=server.project, notification_type='server_alert')

        # Check Exbots
        expiring_exbots = ProjectExbot.objects.filter(
            plan_deactive_date__gte=today,
            plan_deactive_date__lte=max_date
        )
        for exbot in expiring_exbots:
            days_remaining = (exbot.plan_deactive_date - today).days
            message = (
                f"Exbot Expiry Alert: The exbot '{exbot.whatsapp_number}' ({exbot.plan_category}) for project "
                f"'{exbot.project.name if exbot.project else 'N/A'}' is expiring on "
                f"{exbot.plan_deactive_date} ({days_remaining} days remaining). "
                f"Action Required: Please ensure payment is processed or plan is renewed to avoid service interruption."
            )
            create_notification_if_new(superadmins, message, project=exbot.project, notification_type='exbot_alert')

    def get(self, request):
        if not request.user.has_perm('djangosimplemissionapp.view_projectstats'):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
            
        # Auto-trigger expiry check every time this API is called
        self._run_expiry_check()

        from .models import Project, ProjectService, ProjectFinance, ProjectTeam, ProjectServiceTeam
        from rest_framework.pagination import PageNumberPagination
        
        projects = Project.objects.prefetch_related(
            'services', 'project_finances', 'project_teams__team'
        ).order_by('-created_at')
        
        # 1. Search Filter
        search_query = request.query_params.get('search', '')
        if search_query:
            projects = projects.filter(name__icontains=search_query)
            
        # 2. Date Filter
        date_q = get_financial_date_filter(request, 'created_at')
        if date_q:
            projects = projects.filter(date_q)

        # 3. Status Filter (New Interactivity)
        status_filter = request.query_params.get('status', '').lower()
        if status_filter:
            if status_filter == 'pending':
                projects = projects.filter(status__iexact='pending')
            elif status_filter == 'progressing':
                projects = projects.exclude(status__iexact='completed').exclude(status__iexact='done').exclude(status__iexact='pending')
            elif status_filter == 'completed':
                projects = projects.filter(Q(status__iexact='completed') | Q(status__iexact='done'))

        # 4. Payment Status Filter
        payment_status_filter = request.query_params.get('payment_status', '').lower()
        if payment_status_filter:
            unpaid_q = (
                Q(project_finances__total_balance_due__gt=0) |
                Q(project_domains__payment_status='UNPAID') |
                Q(project_servers__payment_status='UNPAID') |
                Q(services__payment_status='UNPAID')
            )
            if payment_status_filter == 'unpaid':
                projects = projects.filter(unpaid_q).distinct()
            elif payment_status_filter == 'paid':
                projects = projects.exclude(unpaid_q).distinct()

        # 5. Team Status Filter
        team_status_filter = request.query_params.get('team_status', '').lower()
        if team_status_filter:
            from .models import ProjectTeam, ProjectServiceTeam
            
            unfinished_pt_project_ids = ProjectTeam.objects.exclude(status__iexact='completed').exclude(status__iexact='done').values_list('project_id', flat=True)
            unfinished_st_project_ids = ProjectServiceTeam.objects.exclude(status__iexact='completed').exclude(status__iexact='done').values_list('service__project_id', flat=True)
            
            has_unfinished_project_ids = set(unfinished_pt_project_ids) | set(unfinished_st_project_ids)
            
            if team_status_filter == 'unfinished':
                projects = projects.filter(id__in=has_unfinished_project_ids).distinct()
            elif team_status_filter == 'finished':
                has_teams_q = Q(project_teams__isnull=False) | Q(services__teams__isnull=False)
                projects = projects.exclude(id__in=has_unfinished_project_ids).filter(has_teams_q).distinct()
            elif team_status_filter == 'overdue':
                # Filter projects that have at least one overdue team (Project or Service)
                overdue_pt = ProjectTeam.objects.exclude(status__iregex=r'^(completed|done)$').filter(deadline__lt=today).values_list('project_id', flat=True)
                overdue_st = ProjectServiceTeam.objects.exclude(status__iregex=r'^(completed|done)$').filter(deadline__lt=today).values_list('service__project_id', flat=True)
                has_overdue_ids = set(overdue_pt) | set(overdue_st)
                projects = projects.filter(id__in=has_overdue_ids).distinct()
                
        today = timezone.now().date()
        
        # --- Overview Aggregation (Before Pagination) ---
        # Note: getattr/getattr-like checks are needed because status can be on base_info or project
        pending_count = 0
        progressing_count = 0
        completed_count = 0
        unpaid_project_count = 0
        unfinished_teams = 0
        overdue_teams_count = 0
        
        # Aggregate before pagination for Pulse stats
        # We perform counts on the projects queryset that only has date/search filters (not status filter yet)
        pulse_projects = projects if not status_filter else projects.all() # simplified
        
        # Let's use a separate loop or better queryset for overview to ensure it doesn't change when we filter BY status
        # Actually, usually Pulse numbers represent the WHOLE filtered set.
        # But if you click 'Pending', should Pulse change? usually NO, it stays as the constant summary.
        # So we use the 'unfiltered-by-status' projects list for Overview.
        
        # Re-apply date/search only for overview
        ov_projects = Project.objects.filter(date_q) if date_q else Project.objects.all()
        if search_query: ov_projects = ov_projects.filter(name__icontains=search_query)

        total_teams = 0
        for p in ov_projects:
            # Status check
            base_info = p.project_base_informations.first()
            p_status = (getattr(base_info, 'status', p.status) if base_info else p.status).lower()
            
            if 'pending' in p_status: pending_count += 1
            elif 'progressing' in p_status or 'active' in p_status or 'in_progress' in p_status: progressing_count += 1
            elif 'completed' in p_status or 'done' in p_status: completed_count += 1
            
            # Comprehensive Payment Status Check
            is_unpaid = p.project_finances.filter(total_balance_due__gt=0).exists() or \
                        p.project_domains.filter(payment_status__iexact='UNPAID').exists() or \
                        p.project_servers.filter(payment_status__iexact='UNPAID').exists() or \
                        p.project_exbots.filter(payment_status__iexact='UNPAID').exists() or \
                        p.services.filter(payment_status__iexact='UNPAID').exists() or \
                        p.project_teams.filter(payment_status__iexact='UNPAID').exists()
            
            if is_unpaid: 
                unpaid_project_count += 1
            
            # Work check (Unfinished teams)
            unfinished_teams += p.project_teams.exclude(status__iexact='completed').exclude(status__iexact='done').count()
            unfinished_teams += ProjectServiceTeam.objects.filter(service__project=p).exclude(status__iexact='completed').exclude(status__iexact='done').count()
            
            # Overdue check (Specifically for Critical cards)
            overdue_teams_count += p.project_teams.exclude(status__iregex=r'^(completed|done)$').filter(deadline__lt=today).count()
            overdue_teams_count += ProjectServiceTeam.objects.filter(service__project=p).exclude(status__iregex=r'^(completed|done)$').filter(deadline__lt=today).count()
            
            # Total stats
            total_teams += p.project_teams.count()
            total_teams += ProjectServiceTeam.objects.filter(service__project=p).count()

        total_ov_remaining_amount = 0.0
        for p in ov_projects:
            # Calculate properly for EACH project in overview loop with case-insensitive filters
            t_total = float(p.project_teams.aggregate(t=Sum('cost'))['t'] or 0.0)
            t_paid = float(p.project_teams.filter(payment_status__iexact='PAID').aggregate(t=Sum('cost'))['t'] or 0.0)
            s_total = float(p.services.aggregate(s=Sum('cost'))['s'] or 0.0)
            s_paid = float(p.services.filter(payment_status__iexact='PAID').aggregate(s=Sum('cost'))['s'] or 0.0)
            d_total = float(p.project_domains.aggregate(d=Sum('cost'))['d'] or 0.0)
            d_paid = float(p.project_domains.filter(payment_status__iexact='PAID').aggregate(d=Sum('cost'))['d'] or 0.0)
            srv_total = float(p.project_servers.aggregate(v=Sum('cost'))['v'] or 0.0)
            srv_paid = float(p.project_servers.filter(payment_status__iexact='PAID').aggregate(v=Sum('cost'))['v'] or 0.0)
            ex_total = float(p.project_exbots.aggregate(e=Sum('plan_rate'))['e'] or 0.0)
            ex_paid = float(p.project_exbots.filter(payment_status__iexact='PAID').aggregate(e=Sum('plan_rate'))['e'] or 0.0)
            
            p_total = t_total + s_total + d_total + srv_total + ex_total
            p_paid = t_paid + s_paid + d_paid + srv_paid + ex_paid
            total_ov_remaining_amount += (p_total - p_paid)

        overview_data = {
            "projects": {
                "pending": pending_count,
                "progressing": progressing_count,
                "completed": completed_count,
                "total": ov_projects.count()
            },
            "payment": {
                "unpaid_projects": unpaid_project_count,
                "paid_projects": ov_projects.count() - unpaid_project_count,
                "total_remaining_amount": total_ov_remaining_amount
            },
            "work": {
                "unfinished_teams": unfinished_teams,
                "overdue_teams": overdue_teams_count,
                "total_teams": total_teams
            }
        }
        
        # --- Pagination ---
        paginator = PageNumberPagination()
        paginator.page_size = int(request.query_params.get('page_size', 10))
        paginated_projects = paginator.paginate_queryset(projects, request)
        
        results = []

        for project in paginated_projects:
            # Base info
            base_info = project.project_base_informations.first()
            project_name = base_info.name if base_info else project.name
            project_status = getattr(base_info, 'status', project.status) if base_info else project.status
            
            # Project teams
            p_teams = list(project.project_teams.all())
            project_team_names = ", ".join(pt.team.name for pt in p_teams if pt.team)
            pt_status = 'No Team'
            if p_teams:
                unfinished_pts = [t.status for t in p_teams if t.status.lower() not in ['completed', 'done']]
                pt_status = unfinished_pts[0] if unfinished_pts else p_teams[0].status
            
            # Domain Payment Status counts
            domains = project.project_domains.all()
            paid_domains = domains.filter(payment_status__iexact='PAID').count()
            unpaid_domains = domains.filter(payment_status__iexact='UNPAID').count()
            total_domains = domains.count()
            domain_payment_str = "No Domain"
            if total_domains > 0:
                domain_payment_str = "Paid" if paid_domains == total_domains else f"Unpaid ({paid_domains}/{total_domains} Paid)"

            # Server Payment Status counts
            servers = project.project_servers.all()
            paid_servers = servers.filter(payment_status__iexact='PAID').count()
            unpaid_servers = servers.filter(payment_status__iexact='UNPAID').count()
            total_servers = servers.count()
            server_payment_str = "No Server"
            if total_servers > 0:
                server_payment_str = "Paid" if paid_servers == total_servers else f"Unpaid ({paid_servers}/{total_servers} Paid)"

            # Exbot counts
            exbots = project.project_exbots.all()
            paid_exbots = exbots.filter(payment_status__iexact='PAID').count()
            unpaid_exbots = exbots.filter(payment_status__iexact='UNPAID').count()
            total_exbots = exbots.count()
            exbot_payment_str = "No Bot"
            if total_exbots > 0:
                exbot_payment_str = "Paid" if paid_exbots == total_exbots else f"Unpaid ({paid_exbots}/{total_exbots} Paid)"

            # Finance & Details (DYNAMIC AGGREGATION FROM NEW COST FIELDS)
            # 1. Teams
            teams_total = float(project.project_teams.aggregate(total=Sum('cost'))['total'] or 0.0)
            teams_paid = float(project.project_teams.filter(payment_status__iexact='PAID').aggregate(total=Sum('cost'))['total'] or 0.0)
            
            # 2. Services
            p_srvs = project.services.all()
            services_total = float(p_srvs.aggregate(total=Sum('cost'))['total'] or 0.0)
            services_paid = float(p_srvs.filter(payment_status__iexact='PAID').aggregate(total=Sum('cost'))['total'] or 0.0)
            
            # 3. Domains
            domains_total = float(domains.aggregate(total=Sum('cost'))['total'] or 0.0)
            domains_paid = float(domains.filter(payment_status__iexact='PAID').aggregate(total=Sum('cost'))['total'] or 0.0)
            
            # 4. Servers
            servers_total = float(servers.aggregate(total=Sum('cost'))['total'] or 0.0)
            servers_paid = float(servers.filter(payment_status__iexact='PAID').aggregate(total=Sum('cost'))['total'] or 0.0)
            
            # 5. Exbots
            exbots_total = float(exbots.aggregate(total=Sum('plan_rate'))['total'] or 0.0)
            exbots_paid = float(exbots.filter(payment_status__iexact='PAID').aggregate(total=Sum('plan_rate'))['total'] or 0.0)
            
            # Final Totals
            total_project_cost = teams_total + services_total + domains_total + servers_total + exbots_total
            total_paid = teams_paid + services_paid + domains_paid + servers_paid + exbots_paid
            balance_due = total_project_cost - total_paid
            
            domain_cost = domains_total
            server_cost = servers_total
            service_cost = services_total
            project_cost = teams_total
            
            domain_deadline = domains.aggregate(Min('expiration_date'))['expiration_date__min'] if domains.exists() else None
            server_deadline = servers.aggregate(Min('expiration_date'))['expiration_date__min'] if servers.exists() else None

            # Granular Team counts for "X/Y Complete"
            project_teams_qs = project.project_teams.all()
            service_teams_qs = ProjectServiceTeam.objects.filter(service__project=project)
            
            p_total = project_teams_qs.count()
            p_done = project_teams_qs.filter(status__iregex=r'^(completed|done)$').count()
            
            s_total = service_teams_qs.count()
            s_done = service_teams_qs.filter(status__iregex=r'^(completed|done)$').count()
            
            total_teams_count = p_total + s_total
            completed_teams_count = p_done + s_done

            category_status = {
                "project": "Paid" if (completed_teams_count == total_teams_count) else "Unpaid",
                "project_total_cost": teams_total,
                "project_paid_cost": teams_paid,
                "project_unpaid_cost": teams_total - teams_paid,
                
                "domain": "Paid" if (paid_domains == total_domains) else "Unpaid",
                "domain_total_cost": domains_total,
                "domain_paid_cost": domains_paid,
                "domain_unpaid_cost": domains_total - domains_paid,
                "domain_deadline": domain_deadline,
                "domain_items": [
                    {
                        "name": d.name,
                        "cost": float(d.cost or 0.0),
                        "payment_status": d.payment_status,
                        "deadline": d.expiration_date.strftime('%Y-%m-%d') if d.expiration_date else None
                    } for d in domains
                ],
                "server": "Paid" if (paid_servers == total_servers) else "Unpaid",
                "server_total_cost": servers_total,
                "server_paid_cost": servers_paid,
                "server_unpaid_cost": servers_total - servers_paid,
                "server_deadline": server_deadline,
                "server_items": [
                    {
                        "name": s.name,
                        "cost": float(s.cost or 0.0),
                        "payment_status": s.payment_status,
                        "deadline": s.expiration_date.strftime('%Y-%m-%d') if s.expiration_date else None
                    } for s in servers
                ],
                "service": "Paid" if (p_srvs.filter(payment_status__iexact='PAID').count() == p_srvs.count()) else "Unpaid",
                "service_total_cost": services_total,
                "service_paid_cost": services_paid,
                "service_unpaid_cost": services_total - services_paid,

                "exbot": "Paid" if (paid_exbots == total_exbots) else "Unpaid",
                "exbot_total_cost": exbots_total,
                "exbot_paid_cost": exbots_paid,
                "exbot_unpaid_cost": exbots_total - exbots_paid,
                "exbot_items": [
                    {
                        "whatsapp": ex.whatsapp_number,
                        "cost": float(ex.plan_rate or 0.0),
                        "payment_status": ex.payment_status,
                        "deadline": ex.plan_deactive_date.strftime('%Y-%m-%d') if ex.plan_deactive_date else None
                    } for ex in exbots
                ],
            }



            # Expiration Counts (Within 30 days) - Include ALL (Paid + Unpaid) and Only Latest
            soon = today + timedelta(days=30)
            
            # Deduplicate servers for this project to get latest only
            proj_servers = project.project_servers.all().order_by('server_type', 'name', '-expiration_date')
            latest_proj_servers = []
            seen_s = set()
            for s in proj_servers:
                key = (s.server_type, s.name)
                if key not in seen_s:
                    latest_proj_servers.append(s)
                    seen_s.add(key)
            
            server_expiring_soon_count = len([s for s in latest_proj_servers if s.expiration_date and today <= s.expiration_date <= soon])

            # Deduplicate domains for this project
            proj_domains = project.project_domains.all().order_by('name', '-expiration_date')
            latest_proj_domains = []
            seen_d = set()
            for d in proj_domains:
                key = (d.name)
                if key not in seen_d:
                    latest_proj_domains.append(d)
                    seen_d.add(key)
                    
            domain_expiring_soon_count = len([d for d in latest_proj_domains if d.expiration_date and today <= d.expiration_date <= soon])

            # Deduplicate exbots for this project
            proj_exbots = project.project_exbots.all().order_by('whatsapp_number', '-plan_deactive_date')
            latest_proj_exbots = []
            seen_e = set()
            for ex in proj_exbots:
                key = (ex.whatsapp_number)
                if key not in seen_e:
                    latest_proj_exbots.append(ex)
                    seen_e.add(key)
            
            exbot_expiring_soon_count = len([ex for ex in latest_proj_exbots if ex.plan_deactive_date and today <= ex.plan_deactive_date <= soon])

            services_data = []
            for service in project.services.all():
                svc_teams = list(service.teams.all())
                st_status = 'No Team'
                if svc_teams:
                    unfinished_sts = [t.status for t in svc_teams if t.status.lower() not in ['completed', 'done']]
                    st_status = unfinished_sts[0] if unfinished_sts else svc_teams[0].status
                    
                services_data.append({
                    "service_team_name": ", ".join(st.team.name for st in svc_teams if st.team) or "No Team",
                    "status": service.status,
                    "service_team_status": st_status,
                    "paid_status": service.payment_status,
                    "service_team_start_date": service.teams.aggregate(Min('start_date'))['start_date__min'],
                    "service_team_deadline": service.teams.aggregate(Max('deadline'))['deadline__max'],
                    "service_cost": float(service.cost or 0.0),
                })

            project_result = {
                "project_id": project.id,
                "project_name": project_name,
                "project_team_name": project_team_names or "No Team",
                "project_team_status": pt_status,
                "status": project_status,
                "total_paid": total_paid,
                "balance_due": balance_due,
                "total_project_cost": total_project_cost,
                "project_cost": project_cost,
                "category_status": category_status,
                "project_payment": category_status["project"], # Legacy
                "domain_payment": domain_payment_str, 
                "server_payment": server_payment_str,
                "exbot_payment": exbot_payment_str,
                "project_team_start_date": project.project_teams.aggregate(Min('start_date'))['start_date__min'],
                "project_team_deadline": project.project_teams.aggregate(Max('deadline'))['deadline__max'],
                "serviceteam_count": project.services.count(),
                "server_count": total_servers,
                "paid_server_count": paid_servers,
                "unpaid_server_count": unpaid_servers,
                "domain_count": total_domains,
                "paid_domain_count": paid_domains,
                "unpaid_domain_count": unpaid_domains,
                "exbot_count": total_exbots,
                "paid_exbot_count": paid_exbots,
                "unpaid_exbot_count": unpaid_exbots,
                "server_name": servers.first().name if servers.exists() else "No Server",
                "domain_name": domains.first().name if domains.exists() else "No Domain",
                "exbot_name": exbots.first().whatsapp_number if exbots.exists() else "No Bot",
                "total_teams_count": total_teams_count,
                "completed_teams_count": completed_teams_count,
                "server_expiring_soon_count": server_expiring_soon_count,
                "domain_expiring_soon_count": domain_expiring_soon_count,
                "exbot_expiring_soon_count": exbot_expiring_soon_count,
                "services": services_data
            }
            results.append(project_result)

        # Build final paginated response
        response_data = {
            'overview': overview_data,
            'total_project_count': paginator.page.paginator.count,
            'next': paginator.get_next_link(),
            'previous': paginator.get_previous_link(),
            'results': results
        }

        return Response(response_data, status=status.HTTP_200_OK)

class ServerAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.has_perm('djangosimplemissionapp.view_server_stats'):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
            
        from .models import ProjectServer
        from django.db.models import Count, Sum
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        next_30_days = today + timedelta(days=30)

        # Get all servers ordered to help deduplication (latest expiration first)
        all_servers = ProjectServer.objects.all().select_related('project').order_by('project_id', 'server_type', 'name', '-expiration_date')
        
        # Deduplicate: Only keep the latest record for each (Project, Type, Name)
        servers_list_latest = []
        seen_keys = set()
        for s in all_servers:
            key = (s.project_id, s.server_type, s.name)
            if key not in seen_keys:
                servers_list_latest.append(s)
                seen_keys.add(key)

        # Totals based on latest servers only
        total_servers = len(servers_list_latest)
        paid_servers_count = len([s for s in servers_list_latest if s.payment_status == 'PAID'])
        unpaid_servers_count = len([s for s in servers_list_latest if s.payment_status == 'UNPAID'])
        total_cost = sum([s.cost for s in servers_list_latest if s.cost])

        # Status counts based on latest servers & expiry date
        computed_expired = len([s for s in servers_list_latest if (s.expiration_date and s.expiration_date < today) or (s.status and s.status.lower() == 'expired')])
        computed_active = len([s for s in servers_list_latest if s.status and s.status.lower() == 'active' and not (s.expiration_date and s.expiration_date < today)])
        
        # Expiring Soon: Include BOTH Paid and Unpaid
        computed_expiring_soon = len([s for s in servers_list_latest if s.expiration_date and today <= s.expiration_date <= next_30_days])

        # Grouping (re-calculating based on latest set)
        by_server_type_dict = {}
        by_accrued_by_dict = {}
        
        for s in servers_list_latest:
            by_server_type_dict[s.server_type] = by_server_type_dict.get(s.server_type, 0) + 1
            by_accrued_by_dict[s.accrued_by] = by_accrued_by_dict.get(s.accrued_by, 0) + 1
            
        by_server_type = [{"server_type": k, "count": v} for k, v in by_server_type_dict.items()]
        by_accrued_by = [{"accrued_by": k, "count": v} for k, v in by_accrued_by_dict.items()]

        # All servers detailed list for drill-down
        detailed_servers_list = []
        for s in servers_list_latest:
            days_until_expiry = None
            if s.expiration_date:
                days_until_expiry = (s.expiration_date - today).days

            detailed_servers_list.append({
                "id": s.id,
                "name": s.name,
                "server_type": s.server_type,
                "expiration_date": s.expiration_date.strftime('%Y-%m-%d') if s.expiration_date else None,
                "purchase_date": s.purchase_date.strftime('%Y-%m-%d') if s.purchase_date else None,
                "project": s.project.name if s.project else None,
                "payment_status": s.payment_status,
                "status": s.status,
                "cost": float(s.cost) if s.cost else 0.0,
                "accrued_by": s.accrued_by,
                "purchased_from": s.purchased_from,
                "days_until_expiry": days_until_expiry,
            })

        # Expiring soon list
        expiring_soon = [s for s in detailed_servers_list if s["days_until_expiry"] is not None and 0 <= s["days_until_expiry"] <= 30]

        # SORTING: Expiring Soon (0-30 days) first, then Active, then Expired last
        detailed_servers_list.sort(
            key=lambda x: (
                0 if x["days_until_expiry"] is not None and 0 <= x["days_until_expiry"] <= 30 else
                1 if x["days_until_expiry"] is None or x["days_until_expiry"] > 30 else
                2,
                x["days_until_expiry"] if x["days_until_expiry"] is not None else 9999
            )
        )

        data = {
            "overview": {
                "total_servers": total_servers,
                "active_servers": computed_active,
                "expired_servers": computed_expired,
                "expiring_soon_count": computed_expiring_soon,
                "paid_servers": paid_servers_count,
                "unpaid_servers": unpaid_servers_count,
                "total_cost": float(total_cost)
            },
            "by_server_type": by_server_type,
            "by_accrued_by": by_accrued_by,
            "expiring_soon": expiring_soon,
            "servers_list": detailed_servers_list
        }
        return Response(data, status=status.HTTP_200_OK)

class DomainAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.has_perm('djangosimplemissionapp.view_domain_stats'):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
            
        from .models import ProjectDomain
        from django.db.models import Count, Sum
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        next_30_days = today + timedelta(days=30)

        # Get all domains ordered to help deduplication (latest expiration first)
        all_domains = ProjectDomain.objects.all().select_related('project').order_by('project_id', 'name', '-expiration_date')
        
        # Deduplicate: Only keep the latest record for each (Project, Name)
        domains_list_latest = []
        seen_keys = set()
        for d in all_domains:
            key = (d.project_id, d.name)
            if key not in seen_keys:
                domains_list_latest.append(d)
                seen_keys.add(key)

        # Totals based on latest domains only
        total_domains = len(domains_list_latest)
        # Status counts based on latest domains & expiry date
        expired_domains = len([d for d in domains_list_latest if (d.expiration_date and d.expiration_date < today) or (d.status and d.status.lower() == 'expired')])
        active_domains = len([d for d in domains_list_latest if d.status and d.status.lower() == 'active' and not (d.expiration_date and d.expiration_date < today)])
        paid_domains_count = len([d for d in domains_list_latest if d.payment_status == 'PAID'])
        unpaid_domains_count = len([d for d in domains_list_latest if d.payment_status == 'UNPAID'])
        total_cost = sum([d.cost for d in domains_list_latest if d.cost])

        # Expiring Soon: Include BOTH Paid and Unpaid
        computed_expiring_soon = len([d for d in domains_list_latest if d.expiration_date and today <= d.expiration_date <= next_30_days])

        # Group by accrued by
        by_accrued_by_dict = {}
        for d in domains_list_latest:
            by_accrued_by_dict[d.accrued_by] = by_accrued_by_dict.get(d.accrued_by, 0) + 1
        by_accrued_by = [{"accrued_by": k, "count": v} for k, v in by_accrued_by_dict.items()]

        # All domains detailed list for drill-down
        detailed_domains_list = []
        for d in domains_list_latest:
            days_until_expiry = None
            if d.expiration_date:
                days_until_expiry = (d.expiration_date - today).days

            detailed_domains_list.append({
                "id": d.id,
                "name": d.name,
                "domain": d.name,
                "expiration_date": d.expiration_date.strftime('%Y-%m-%d') if d.expiration_date else None,
                "purchase_date": d.purchase_date.strftime('%Y-%m-%d') if d.purchase_date else None,
                "project": d.project.name if d.project else None,
                "payment_status": d.payment_status,
                "status": d.status,
                "cost": float(d.cost) if d.cost else 0.0,
                "accrued_by": d.accrued_by,
                "purchased_from": d.purchased_from,
                "days_until_expiry": days_until_expiry,
            })

        # Expiring soon list
        expiring_soon = [d for d in detailed_domains_list if d["days_until_expiry"] is not None and 0 <= d["days_until_expiry"] <= 30]

        # SORTING: Expiring Soon (0-30 days) first, then Active, then Expired last
        detailed_domains_list.sort(
            key=lambda x: (
                0 if x["days_until_expiry"] is not None and 0 <= x["days_until_expiry"] <= 30 else
                1 if x["days_until_expiry"] is None or x["days_until_expiry"] > 30 else
                2,
                x["days_until_expiry"] if x["days_until_expiry"] is not None else 9999
            )
        )

        data = {
            "overview": {
                "total_domains": total_domains,
                "active_domains": active_domains,
                "expired_domains": expired_domains,
                "expiring_soon_count": computed_expiring_soon,
                "paid_domains": paid_domains_count,
                "unpaid_domains": unpaid_domains_count,
                "total_cost": float(total_cost)
            },
            "by_accrued_by": by_accrued_by,
            "expiring_soon": expiring_soon,
            "domains_list": detailed_domains_list
        }

        return Response(data, status=status.HTTP_200_OK)

class ExbotAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.has_perm('djangosimplemissionapp.view_exbot_stats'):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        
        from .models import ProjectExbot
        from django.db.models import Count, Sum
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        next_30_days = today + timedelta(days=30)

        # Get all exbots
        all_exbots = ProjectExbot.objects.all().select_related('project').order_by('project_id', 'whatsapp_number', '-plan_deactive_date')
        
        exbots_list = list(all_exbots)

        total_exbots = len(exbots_list)
        
        # Status counts
        expired_exbots = len([e for e in exbots_list if (e.plan_deactive_date and e.plan_deactive_date < today) or (e.status and e.status.lower() == 'expired')])
        active_exbots = len([e for e in exbots_list if e.status and e.status.lower() == 'active' and not (e.plan_deactive_date and e.plan_deactive_date < today)])
        paid_exbots_count = len([e for e in exbots_list if e.payment_status == 'PAID'])
        unpaid_exbots_count = len([e for e in exbots_list if e.payment_status == 'UNPAID'])
        total_cost = sum([e.plan_rate for e in exbots_list if e.plan_rate])

        # Expiring Soon
        computed_expiring_soon = len([e for e in exbots_list if e.plan_deactive_date and today <= e.plan_deactive_date <= next_30_days])

        # Group by category
        by_category_dict = {}
        for e in exbots_list:
            cat = e.plan_category or "Unknown"
            by_category_dict[cat] = by_category_dict.get(cat, 0) + 1
        by_category = [{"plan_category": k, "count": v} for k, v in by_category_dict.items()]

        # Detailed list
        detailed_exbots_list = []
        for e in exbots_list:
            days_until_expiry = None
            if e.plan_deactive_date:
                days_until_expiry = (e.plan_deactive_date - today).days

            detailed_exbots_list.append({
                "id": e.id,
                "whatsapp_number": e.whatsapp_number,
                "plan_category": e.plan_category,
                "active_date": e.plan_active_date.strftime('%Y-%m-%d') if e.plan_active_date else None,
                "deactive_date": e.plan_deactive_date.strftime('%Y-%m-%d') if e.plan_deactive_date else None,
                "project": e.project.name if e.project else None,
                "payment_status": e.payment_status,
                "status": e.status,
                "plan_rate": float(e.plan_rate) if e.plan_rate else 0.0,
                "days_until_expiry": days_until_expiry,
                "description": e.description,
            })

        # SORTING: Expiring Soon (0-30 days) first, then Active, then Expired last
        detailed_exbots_list.sort(
            key=lambda x: (
                0 if x["days_until_expiry"] is not None and 0 <= x["days_until_expiry"] <= 30 else
                1 if x["days_until_expiry"] is None or x["days_until_expiry"] > 30 else
                2,
                x["days_until_expiry"] if x["days_until_expiry"] is not None else 9999
            )
        )

        data = {
            "overview": {
                "total_exbots": total_exbots,
                "active_exbots": active_exbots,
                "expired_exbots": expired_exbots,
                "expiring_soon_count": computed_expiring_soon,
                "paid_exbots": paid_exbots_count,
                "unpaid_exbots": unpaid_exbots_count,
                "total_cost": float(total_cost)
            },
            "by_category": by_category,
            "expiring_soon": [e for e in detailed_exbots_list if e["days_until_expiry"] is not None and 0 <= e["days_until_expiry"] <= 30],
            "exbots_list": detailed_exbots_list
        }
        return Response(data, status=status.HTTP_200_OK)
