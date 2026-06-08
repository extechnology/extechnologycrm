from django.db import models
from rest_framework import serializers
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth.models import Permission
from .models import (
    User,Role,ProjectClient,ProjectBusinessAddress,DomainOrServerThirdPartyServiceProvider,
    ProjectDomain,ProjectServer,ProjectFinance,Team,ProjectTeam,ProjectNature,
    Project,ProjectBaseInformation,ProjectExcution,ProjectTeamMember,ProjectService,
    ProjectServiceTeam,ProjectServiceMember,ProjectDocument,
    EmployeeDailyActivity,ActivityLog,Invoice,InvoiceItem,Payment,ActivityExceedComment,
    Notification,EmployeeLeave,Company,CompanyProfile,Salary,Attendance,Employee,OtherIncome,OtherExpense,UserSalary,SalaryIncrement,
    ClientAdvance,ProjectExbot,Lead,FollowUp,Schedule
)
class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename']

class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(),
        many=True,
        write_only=True,
        source='permissions',
        required=False
    )
    
    class Meta:
        model = Role
        fields = ['id', 'name', 'permissions', 'permission_ids']

class UserSerializer(serializers.ModelSerializer):

    role = RoleSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        write_only=True,
        source='role',
        required=False,
        allow_null=True
    )

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'phone_number',
            'designation',
            'profile_pic',
            'role',
            'role_id',
            'date_joined',
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

class AdminChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True)


class ProjectClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectClient
        fields = '__all__'  
        extra_kwargs = {'id': {'read_only': False, 'required': False, 'allow_null': True}}


class ProjectBusinessAddressSerializer(serializers.ModelSerializer):
    # This will show a list of project names/IDs linked to this address
    projects = serializers.SerializerMethodField()

    class Meta:
        model = ProjectBusinessAddress
        fields = '__all__'  
        extra_kwargs = {'id': {'read_only': False, 'required': False, 'allow_null': True}}

    def get_projects(self, obj):
        return [{"id": p.id, "name": p.name} for p in obj.projects.all()]

class ClientAdvanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientAdvance
        fields = '__all__'
        extra_kwargs = {
            'id': {'read_only': False, 'required': False, 'allow_null': True},
            'remaining_amount': {'read_only': False, 'required': False},
            'advance_balance': {'read_only': False, 'required': False},
        }

class ClientSummarySerializer(serializers.ModelSerializer):
    total_invoiced = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    total_balance_due = serializers.SerializerMethodField()
    invoice_count = serializers.SerializerMethodField()
    total_advance = serializers.SerializerMethodField()
    remaining_advance = serializers.SerializerMethodField()

    class Meta:
        model = ProjectBusinessAddress
        fields = ['id', 'legal_name', 'total_invoiced', 'total_paid', 'total_balance_due', 'invoice_count', 'total_advance', 'remaining_advance']

    def get_total_invoiced(self, obj):
        invoices = obj.invoices.all()
        request = self.context.get('request')
        if request:
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            if start_date:
                invoices = invoices.filter(created_at__date__gte=start_date)
            if end_date:
                invoices = invoices.filter(created_at__date__lte=end_date)
        return invoices.aggregate(total=models.Sum('total_amount'))['total'] or 0

    def get_total_paid(self, obj):
        invoices = obj.invoices.all()
        request = self.context.get('request')
        if request:
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            if start_date:
                invoices = invoices.filter(created_at__date__gte=start_date)
            if end_date:
                invoices = invoices.filter(created_at__date__lte=end_date)
        return invoices.aggregate(total=models.Sum('total_paid'))['total'] or 0

    def get_total_balance_due(self, obj):
        invoices = obj.invoices.all()
        request = self.context.get('request')
        if request:
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            if start_date:
                invoices = invoices.filter(created_at__date__gte=start_date)
            if end_date:
                invoices = invoices.filter(created_at__date__lte=end_date)
        return invoices.aggregate(total=models.Sum('balance_due'))['total'] or 0

    def get_invoice_count(self, obj):
        invoices = obj.invoices.all()
        request = self.context.get('request')
        if request:
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            if start_date:
                invoices = invoices.filter(created_at__date__gte=start_date)
            if end_date:
                invoices = invoices.filter(created_at__date__lte=end_date)
        return invoices.count()

    def get_total_advance(self, obj):
        return obj.advances.aggregate(total=models.Sum('amount'))['total'] or 0

    def get_remaining_advance(self, obj):
        return obj.advances.aggregate(total=models.Sum('remaining_amount'))['total'] or 0

    def update(self, instance, validated_data):
        # If user manually edits remaining_amount, calculate initial_usage
        new_remaining = validated_data.get('remaining_amount')
        if new_remaining is not None and new_remaining != instance.remaining_amount:
            # Adjustment = Original Amount - What is left now
            # Actually, initial_usage is "Already spent before system application"
            # It's better to calculate it based on current applications too.
            # For simplicity: usage = amount - new_remaining
            instance.initial_usage = instance.amount - Decimal(str(new_remaining))
        
        # Also handle advance_balance similarly for consistency
        new_balance = validated_data.get('advance_balance')
        if new_balance is not None:
             instance.advance_balance = new_balance

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

class FollowUpSerializer(serializers.ModelSerializer):
    lead_name = serializers.ReadOnlyField(source='lead.company_name')
    class Meta:
        model = FollowUp
        fields = ['id', 'lead', 'lead_name', 'note', 'followup_date', 'interaction_date', 'interest_level', 'conversion_status', 'interaction_type', 'status', 'is_project_created', 'created_at']


class LeadSerializer(serializers.ModelSerializer):
    followups = FollowUpSerializer(many=True, read_only=True)
    assigned_to_name = serializers.ReadOnlyField(source='assigned_to.username')
    assigned_role_name = serializers.ReadOnlyField(source='assigned_role.name')
    
    interest_level = serializers.SerializerMethodField()
    conversion_status = serializers.SerializerMethodField()
    next_followup_date = serializers.SerializerMethodField()

    write_interest_level = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    write_conversion_status = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    write_remark = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    write_followup_date = serializers.DateField(write_only=True, required=False, allow_null=True)
    write_interaction_type = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Lead
        fields = '__all__'

    def get_interest_level(self, obj):
        latest = obj.followups.order_by('-created_at').first()
        return latest.interest_level if latest and latest.interest_level else 'warm'

    def get_conversion_status(self, obj):
        latest = obj.followups.order_by('-created_at').first()
        return latest.conversion_status if latest and latest.conversion_status else 'new'

    def get_next_followup_date(self, obj):
        today = timezone.now().date()
        # Try to find the nearest upcoming follow-up
        upcoming = obj.followups.filter(followup_date__gte=today, status='pending').order_by('followup_date').first()
        if upcoming:
            return upcoming.followup_date
        
        # Fallback to the most recent overdue follow-up if no upcoming exists
        overdue = obj.followups.filter(followup_date__lt=today, status='pending').order_by('-followup_date').first()
        return overdue.followup_date if overdue else None

    def create(self, validated_data):
        # We pop these fields but no longer create an automatic FollowUp record 
        # to ensure the timeline starts clean as requested.
        validated_data.pop('write_interest_level', 'warm')
        validated_data.pop('write_conversion_status', 'new')
        validated_data.pop('write_remark', '')
        validated_data.pop('write_followup_date', None)
        validated_data.pop('write_interaction_type', 'call')

        return Lead.objects.create(**validated_data)

    def update(self, instance, validated_data):
        interest_level = validated_data.pop('write_interest_level', None)
        conversion_status = validated_data.pop('write_conversion_status', None)
        remark = validated_data.pop('write_remark', None)
        followup_date = validated_data.pop('write_followup_date', None)
        interaction_type = validated_data.pop('write_interaction_type', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if interest_level or conversion_status or remark or interaction_type:
            latest = instance.followups.order_by('-created_at').first()
            
            # Check if any of the fields actually differ from the latest FollowUp or if a remark is provided
            changed = False
            if remark:
                changed = True
            elif latest:
                if interest_level and interest_level != latest.interest_level:
                    changed = True
                if conversion_status and conversion_status != latest.conversion_status:
                    changed = True
                if followup_date and followup_date != latest.followup_date:
                    changed = True
                if interaction_type and interaction_type != latest.interaction_type:
                    changed = True
            else:
                changed = True # No latest followup exists

            if changed:
                # Mark previous pending follow-ups as completed before creating a new one
                instance.followups.filter(status='pending').update(status='completed')
                FollowUp.objects.create(
                    lead=instance,
                    note=remark or "Lead details updated.",
                    followup_date=followup_date or (latest.followup_date if latest else None),
                    interest_level=interest_level or (latest.interest_level if latest else 'warm'),
                    conversion_status=conversion_status or (latest.conversion_status if latest else 'new'),
                    interaction_type=interaction_type or (latest.interaction_type if latest else 'call')
                )
        return instance

class DomainOrServerThirdPartyServiceProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = DomainOrServerThirdPartyServiceProvider
        fields = '__all__'  
        extra_kwargs = {'id': {'read_only': False, 'required': False, 'allow_null': True}}

class ProjectDomainSerializer(serializers.ModelSerializer):
    provider = DomainOrServerThirdPartyServiceProviderSerializer(many=True, required=False)
    project_name = serializers.ReadOnlyField(source='project.name')

    class Meta:
        model = ProjectDomain
        fields = '__all__'
        extra_kwargs = {'id': {'read_only': False, 'required': False, 'allow_null': True}}

    def create(self, validated_data):
        provider_data = validated_data.pop('provider', [])
        domain = ProjectDomain.objects.create(**validated_data)
        for p_data in provider_data:
            p_data.pop('id', None)  # Remove id if null/present to avoid conflicts
            provider = DomainOrServerThirdPartyServiceProvider.objects.create(**p_data)
            domain.provider.add(provider)
        return domain

    def update(self, instance, validated_data):
        provider_data = validated_data.pop('provider', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if provider_data is not None:
            instance.provider.all().delete()
            for p_data in provider_data:
                p_data.pop('id', None)
                provider = DomainOrServerThirdPartyServiceProvider.objects.create(**p_data)
                instance.provider.add(provider)
        return instance

    def validate(self, attrs):
        request = self.context.get('request')
        if request and request.user:
            user = request.user
            is_admin_or_sa = user.is_superuser
            if hasattr(user, 'has_role'):
                is_admin_or_sa = is_admin_or_sa or user.has_role('SuperAdmin') or user.has_role('Admin')
            
            if not is_admin_or_sa:
                if not user.has_perm('djangosimplemissionapp.viewfinancials_projectdomain'):
                    attrs.pop('cost', None)
                    attrs.pop('invoice_status', None)
                    attrs.pop('payment_status', None)
                if not user.has_perm('djangosimplemissionapp.viewdates_projectdomain'):
                    attrs.pop('purchase_date', None)
                    attrs.pop('expiration_date', None)
        return attrs

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user:
            user = request.user
            is_admin_or_sa = user.is_superuser
            if hasattr(user, 'has_role'):
                is_admin_or_sa = is_admin_or_sa or user.has_role('SuperAdmin') or user.has_role('Admin')
            
            if not is_admin_or_sa:
                has_full_view = user.has_perm('djangosimplemissionapp.view_projectdomain')
                if user.has_perm('djangosimplemissionapp.viewnameonly_projectdomain') and not has_full_view:
                    allowed_fields = {'id', 'name', 'purchased_from'}
                    for field in list(representation.keys()):
                        if field not in allowed_fields:
                            representation.pop(field, None)
                            
                # Check financials
                if not user.has_perm('djangosimplemissionapp.viewfinancials_projectdomain'):
                    representation.pop('cost', None)
                    representation.pop('invoice_status', None)
                    representation.pop('payment_status', None)
                
                # Check dates
                if not user.has_perm('djangosimplemissionapp.viewdates_projectdomain'):
                    representation.pop('purchase_date', None)
                    representation.pop('expiration_date', None)
                    
        return representation


class ProjectServerSerializer(serializers.ModelSerializer):
    provider = DomainOrServerThirdPartyServiceProviderSerializer(many=True, required=False)
    project_name = serializers.ReadOnlyField(source='project.name')

    class Meta:
        model = ProjectServer
        fields = '__all__'
        extra_kwargs = {'id': {'read_only': False, 'required': False, 'allow_null': True}}

    def create(self, validated_data):
        provider_data = validated_data.pop('provider', [])
        server = ProjectServer.objects.create(**validated_data)
        for p_data in provider_data:
            p_data.pop('id', None)
            provider = DomainOrServerThirdPartyServiceProvider.objects.create(**p_data)
            server.provider.add(provider)
        return server

    def update(self, instance, validated_data):
        provider_data = validated_data.pop('provider', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if provider_data is not None:
            instance.provider.all().delete()
            for p_data in provider_data:
                p_data.pop('id', None)
                provider = DomainOrServerThirdPartyServiceProvider.objects.create(**p_data)
                instance.provider.add(provider)
        return instance

    def validate(self, attrs):
        request = self.context.get('request')
        if request and request.user:
            user = request.user
            is_admin_or_sa = user.is_superuser
            if hasattr(user, 'has_role'):
                is_admin_or_sa = is_admin_or_sa or user.has_role('SuperAdmin') or user.has_role('Admin')
            
            if not is_admin_or_sa:
                if not user.has_perm('djangosimplemissionapp.viewfinancials_projectserver'):
                    attrs.pop('cost', None)
                    attrs.pop('invoice_status', None)
                    attrs.pop('payment_status', None)
                if not user.has_perm('djangosimplemissionapp.viewdates_projectserver'):
                    attrs.pop('purchase_date', None)
                    attrs.pop('expiration_date', None)
        return attrs

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user:
            user = request.user
            is_admin_or_sa = user.is_superuser
            if hasattr(user, 'has_role'):
                is_admin_or_sa = is_admin_or_sa or user.has_role('SuperAdmin') or user.has_role('Admin')
            
            if not is_admin_or_sa:
                has_full_view = user.has_perm('djangosimplemissionapp.view_projectserver')
                if user.has_perm('djangosimplemissionapp.viewnameonly_projectserver') and not has_full_view:
                    allowed_fields = {'id', 'name', 'purchased_from'}
                    for field in list(representation.keys()):
                        if field not in allowed_fields:
                            representation.pop(field, None)
                            
                # Check financials
                if not user.has_perm('djangosimplemissionapp.viewfinancials_projectserver'):
                    representation.pop('cost', None)
                    representation.pop('invoice_status', None)
                    representation.pop('payment_status', None)
                
                # Check dates
                if not user.has_perm('djangosimplemissionapp.viewdates_projectserver'):
                    representation.pop('purchase_date', None)
                    representation.pop('expiration_date', None)
                    
        return representation

class ProjectExbotSerializer(serializers.ModelSerializer):
    project_name = serializers.ReadOnlyField(source='project.name')
    class Meta:
        model = ProjectExbot
        fields = '__all__'
        extra_kwargs = {'id': {'read_only': False, 'required': False, 'allow_null': True}}

    def validate(self, attrs):
        request = self.context.get('request')
        if request and request.user:
            user = request.user
            is_admin_or_sa = user.is_superuser
            if hasattr(user, 'has_role'):
                is_admin_or_sa = is_admin_or_sa or user.has_role('SuperAdmin') or user.has_role('Admin')
            
            if not is_admin_or_sa:
                if not user.has_perm('djangosimplemissionapp.viewfinancials_projectexbot'):
                    attrs.pop('plan_rate', None)
                    attrs.pop('payment_status', None)
                    attrs.pop('invoice_status', None)
                if not user.has_perm('djangosimplemissionapp.viewdates_projectexbot'):
                    attrs.pop('plan_active_date', None)
                    attrs.pop('plan_deactive_date', None)
        return attrs

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user:
            user = request.user
            is_admin_or_sa = user.is_superuser
            if hasattr(user, 'has_role'):
                is_admin_or_sa = is_admin_or_sa or user.has_role('SuperAdmin') or user.has_role('Admin')
            
            if not is_admin_or_sa:
                if not user.has_perm('djangosimplemissionapp.viewfinancials_projectexbot'):
                    representation.pop('plan_rate', None)
                    representation.pop('payment_status', None)
                    representation.pop('invoice_status', None)
                
                if not user.has_perm('djangosimplemissionapp.viewdates_projectexbot'):
                    representation.pop('plan_active_date', None)
                    representation.pop('plan_deactive_date', None)
                    
        return representation



class ProjectFinanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectFinance
        fields = '__all__'  
        extra_kwargs = {'id': {'read_only': False, 'required': False, 'allow_null': True}}

class TeamSerializer(serializers.ModelSerializer):
    team_lead_name = serializers.ReadOnlyField(source='team_lead.username')
    member_names = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = '__all__'  
        extra_kwargs = {'id': {'read_only': False, 'required': False, 'allow_null': True}}

    def get_member_names(self, obj):
        return [member.username for member in obj.members.all()]



class ProjectNatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectNature
        fields = '__all__'  
        extra_kwargs = {'id': {'read_only': False, 'required': False, 'allow_null': True}}


class ProjectBaseInformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectBaseInformation
        fields = '__all__'
        extra_kwargs = {'id': {'read_only': False, 'required': False, 'allow_null': True}}

class ProjectExcutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectExcution
        fields = '__all__'
        extra_kwargs = {'id': {'read_only': False, 'required': False, 'allow_null': True}}

class ProjectTeamMemberSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='employee.username')
    class Meta:
        model = ProjectTeamMember
        fields = '__all__'
        extra_kwargs = {'id': {'read_only': False, 'required': False, 'allow_null': True}}

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user:
            user = request.user
            is_admin_or_sa = user.is_superuser
            if hasattr(user, 'has_role'):
                is_admin_or_sa = is_admin_or_sa or user.has_role('SuperAdmin') or user.has_role('Admin')
            
            if not is_admin_or_sa:
                # If they don't have 'alldate' permission, and they are looking at someone else's record, strip dates.
                if instance.employee_id != user.id and not user.has_perm('djangosimplemissionapp.alldate_projectteammember'):
                    representation.pop('start_date', None)
                    representation.pop('end_date', None)
                    representation.pop('allocated_days', None)
                    representation.pop('actual_days_spent', None)
                    representation.pop('cost', None)
        return representation

class ProjectDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDocument
        fields = '__all__'
        extra_kwargs = {
            'id': {'read_only': False, 'required': False, 'allow_null': True},
            'document': {'required': False, 'allow_null': True}
        }




class EmployeeDailyActivitySerializer(serializers.ModelSerializer):
    employee_name = serializers.ReadOnlyField(source='employee.username')
    team_name = serializers.ReadOnlyField(source='team.name')
    project_name = serializers.ReadOnlyField(source='project.name')
    project_service_name = serializers.ReadOnlyField(source='project_service.name')
    comment_count = serializers.SerializerMethodField()
    overdue_days = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    projectstarteddate = serializers.SerializerMethodField()
    projectenddate = serializers.SerializerMethodField()
    servicestartdate = serializers.SerializerMethodField()
    allocateddays = serializers.SerializerMethodField()
    remainingdays = serializers.SerializerMethodField()
    totaluseddays = serializers.SerializerMethodField()

   
    
    class Meta:
        model = EmployeeDailyActivity
        fields = [
            field.name for field in EmployeeDailyActivity._meta.fields
        ] + [
            'employee_name',
            'team_name',
            'project_name',
            'project_service_name',
            'comment_count',
            'overdue_days',
            'is_overdue',
            'projectstarteddate',
            'projectenddate',
            'servicestartdate',
            'allocateddays',
            'remainingdays',
            'totaluseddays',
        ]
        read_only_fields = ['target_work_percentage']

    def get_comment_count(self, obj):
        return obj.exceed_comments.count()
    
    def get_totaluseddays(self, obj):
        start_date = self.get_projectstarteddate(obj)

        if obj.project_service:
            start_date = self.get_servicestartdate(obj)

        if not start_date or not obj.date:
            return 0

        obj_date = obj.date.date() if hasattr(obj.date, 'date') else obj.date
        s_date = start_date.date() if hasattr(start_date, 'date') else start_date

        return (obj_date - s_date).days + 1

    
    def get_overdue_days(self, obj):
        # Cache the result on the instance to prevent running this logic twice per row
        if hasattr(obj, '_cached_overdue_days'):
            return obj._cached_overdue_days

        start_date = None
        allocated_days = 0

        # 1. Project Service logic
        if obj.project_service:
            from .models import ProjectServiceMember

            assignment = ProjectServiceMember.objects.filter(
                service=obj.project_service,
                employee=obj.employee,
                allocated_days__gt=0
            ).order_by('-id').first()

            if assignment and assignment.start_date:
                start_date = assignment.start_date
                allocated_days = assignment.allocated_days

        # 2. Project logic
        elif obj.project:
            from .models import ProjectTeamMember, ProjectTeam

            assignment = ProjectTeamMember.objects.filter(
                project=obj.project,
                employee=obj.employee,
                allocated_days__gt=0
            ).order_by('-id').first()

            if not assignment:
                assignment = ProjectTeamMember.objects.filter(
                    project_allocations__project=obj.project,
                    employee=obj.employee,
                    allocated_days__gt=0
                ).order_by('-id').first()

            if assignment and assignment.start_date:
                start_date = assignment.start_date
                allocated_days = assignment.allocated_days

            if not start_date:
                team = ProjectTeam.objects.filter(
                    project=obj.project,
                    members__employee=obj.employee
                ).order_by('-id').first()

                if team and team.start_date:
                    start_date = team.start_date
                    end = team.deadline or team.end_date

                    if end and end > start_date:
                        allocated_days = (end - start_date).days + 1

        # 3. Calculate overdue math safely
        if not start_date or allocated_days <= 0 or not obj.date:
            obj._cached_overdue_days = 0
            return 0

        # Handles edge cases if obj.date or start_date are different types (datetime vs date)
        obj_date = obj.date.date() if hasattr(obj.date, 'date') else obj.date
        s_date = start_date.date() if hasattr(start_date, 'date') else start_date

        elapsed_days = (obj_date - s_date).days + 1
        obj._cached_overdue_days = max(elapsed_days - allocated_days, 0)

        return obj._cached_overdue_days

    def get_is_overdue(self, obj):
        # This will now use the cached value instantly without querying the database again
        return self.get_overdue_days(obj) > 0

    def get_projectstarteddate(self, obj):
        """Get the project start date from ProjectTeamMember assignment"""
        if obj.project:
            from .models import ProjectTeamMember
            # Get the ProjectTeamMember assignment directly
            assignment = ProjectTeamMember.objects.filter(
                project=obj.project,
                employee=obj.employee
            ).order_by('-id').first()
            if assignment and assignment.start_date:
                return assignment.start_date
        return None

    def get_projectenddate(self, obj):
        """Get the project end date from ProjectTeamMember assignment"""
        if obj.project:
            from .models import ProjectTeamMember
            # Get the ProjectTeamMember assignment directly
            assignment = ProjectTeamMember.objects.filter(
                project=obj.project,
                employee=obj.employee
            ).order_by('-id').first()
            if assignment and assignment.end_date:
                return assignment.end_date
        return None

    def get_servicestartdate(self, obj):
        """Get the service start date"""
        if obj.project_service:
            from .models import ProjectServiceMember
            assignment = ProjectServiceMember.objects.filter(
                service=obj.project_service,
                employee=obj.employee,
                allocated_days__gt=0
            ).order_by('-id').first()
            if assignment and assignment.start_date:
                return assignment.start_date
        return None

    def get_allocateddays(self, obj):
        """Get the total allocated days from ProjectTeamMember assignment"""
        if obj.project_service:
            from .models import ProjectServiceMember
            assignment = ProjectServiceMember.objects.filter(
                service=obj.project_service,
                employee=obj.employee
            ).order_by('-id').first()
            if assignment:
                return assignment.allocated_days
        elif obj.project:
            from .models import ProjectTeamMember
            # Get allocated_days directly from ProjectTeamMember
            assignment = ProjectTeamMember.objects.filter(
                project=obj.project,
                employee=obj.employee
            ).order_by('-id').first()
            if assignment:
                return assignment.allocated_days
        return 0

    def get_remainingdays(self, obj):
        """Get the remaining days for the allocation (allocated - elapsed)"""
        allocated = self.get_allocateddays(obj)
        
        # Get start date from project or service
        start_date = None
        if obj.project:
            start_date = self.get_projectstarteddate(obj)
        elif obj.project_service:
            start_date = self.get_servicestartdate(obj)
        
        if not start_date or allocated <= 0 or not obj.date:
            return 0
        
        obj_date = obj.date.date() if hasattr(obj.date, 'date') else obj.date
        s_date = start_date.date() if hasattr(start_date, 'date') else start_date
        elapsed_days = (obj_date - s_date).days + 1
        return max(allocated - elapsed_days, 0)

    
    def _calculate_target(self, validated_data):
        employee = validated_data.get('employee')
        project_service = validated_data.get('project_service')
        project = validated_data.get('project')
        activity_date = validated_data.get('date')

        if not activity_date or not employee:
            return 0

        start_date = None
        allocated_days = 0

        if project_service:
            from .models import ProjectServiceMember
            assignment = ProjectServiceMember.objects.filter(
                service=project_service, employee=employee, allocated_days__gt=0
            ).order_by('-id').first()
            if assignment and assignment.start_date and getattr(assignment, 'allocated_days', 0) > 0:
                start_date = assignment.start_date
                allocated_days = assignment.allocated_days
        elif project:
            from .models import ProjectTeamMember, ProjectTeam

            # Primary: direct project FK on ProjectTeamMember
            assignment = ProjectTeamMember.objects.filter(
                project=project, employee=employee, allocated_days__gt=0
            ).order_by('-id').first()

            # Fallback 1: find via ProjectTeam.members M2M
            if not assignment:
                assignment = ProjectTeamMember.objects.filter(
                    project_allocations__project=project,
                    employee=employee,
                    allocated_days__gt=0
                ).order_by('-id').first()

            if assignment and assignment.start_date and getattr(assignment, 'allocated_days', 0) > 0:
                start_date = assignment.start_date
                allocated_days = assignment.allocated_days

            # Fallback 2: use ProjectTeam's own start_date + deadline/end_date
            if not start_date:
                team = ProjectTeam.objects.filter(
                    project=project,
                    members__employee=employee
                ).order_by('-id').first()
                if team and team.start_date:
                    start_date = team.start_date
                    end = team.deadline or team.end_date
                    if end and end > start_date:
                        allocated_days = (end - start_date).days + 1

        if start_date and allocated_days > 0:
            elapsed_days = (activity_date - start_date).days + 1
            if elapsed_days <= 0:
                return 0
            target = (elapsed_days / allocated_days) * 100
            return min(int(target), 100)

        return 0

    def create(self, validated_data):
        target = self._calculate_target(validated_data)
        validated_data['target_work_percentage'] = target
        return super().create(validated_data)

    def update(self, instance, validated_data):
        merged_data = {
            'employee': validated_data.get('employee', instance.employee),
            'project': validated_data.get('project', instance.project),
            'project_service': validated_data.get('project_service', instance.project_service),
            'date': validated_data.get('date', instance.date)
        }
        target = self._calculate_target(merged_data)
        validated_data['target_work_percentage'] = target
        return super().update(instance, validated_data)

class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = '__all__'
class InvoiceItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    class Meta:
        model = InvoiceItem
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    class Meta:
        model = Payment
        fields = '__all__'

def update_invoice_totals(invoice):
    """Refined wrapper to call the model-level logic."""
    invoice.update_totals()
class InvoiceSerializer(serializers.ModelSerializer):

    items = InvoiceItemSerializer(many=True)
    payments = PaymentSerializer(many=True, required=False)
    client_company = ProjectBusinessAddressSerializer(required=True, allow_null=False)
    company_profile = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            "id", "invoice_number", "invoice_date", "tax_rate", "discount_amount",
            "subtotal", "tax_amount", "total_amount", "total_paid", "balance_due",
            "status", "due_date", "client_company",
            "company_profile", "items", "payments", "created_at"
        ]

    def get_company_profile(self, obj):
        profile = CompanyProfile.objects.first()
        if profile:
            return CompanyProfileSerializer(profile).data
        return None

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        payments_data = validated_data.pop('payments', [])
        client_company_data = validated_data.pop('client_company', None)

        # Handle client_company creation or lookup
        client_company = None
        if client_company_data:
            # If an ID is provided in the nested data, use it, otherwise create new
            client_id = client_company_data.pop('id', None)
            if client_id:
                client_company = ProjectBusinessAddress.objects.filter(id=client_id).first()
                if client_company:
                    for attr, value in client_company_data.items():
                        setattr(client_company, attr, value)
                    client_company.save()
            
            if not client_company:
                client_company = ProjectBusinessAddress.objects.create(**client_company_data)

        invoice = Invoice.objects.create(client_company=client_company, **validated_data)

        for item in items_data:
            item.pop('id', None)
            item.pop('invoice', None)
            invoice_item = InvoiceItem.objects.create(invoice=invoice, **item)

            # ── Mark linked asset as INVOICED ──
            if invoice_item.project_domain_id:
                from .models import ProjectDomain
                ProjectDomain.objects.filter(pk=invoice_item.project_domain_id).update(invoice_status='INVOICED')
            if invoice_item.project_server_id:
                from .models import ProjectServer
                ProjectServer.objects.filter(pk=invoice_item.project_server_id).update(invoice_status='INVOICED')
            if invoice_item.project_exbot_id:
                from .models import ProjectExbot
                ProjectExbot.objects.filter(pk=invoice_item.project_exbot_id).update(invoice_status='INVOICED')
            if invoice_item.project_service_id:
                from .models import ProjectService
                ProjectService.objects.filter(pk=invoice_item.project_service_id).update(invoice_status='INVOICED')
            if invoice_item.project_team_id:
                from .models import ProjectTeam
                ProjectTeam.objects.filter(pk=invoice_item.project_team_id).update(invoice_status='INVOICED')
            if invoice_item.project_finance_id:
                from .models import ProjectFinance
                ProjectFinance.objects.filter(pk=invoice_item.project_finance_id).update(invoice_status='INVOICED')

        for payment in payments_data:
            payment.pop('id', None)
            payment.pop('invoice', None)
            Payment.objects.create(invoice=invoice, **payment)

        update_invoice_totals(invoice)
        return invoice

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        payments_data = validated_data.pop('payments', None)
        client_company_data = validated_data.pop('client_company', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if client_company_data:
            client_instance = instance.client_company
            if client_instance:
                # Update existing client
                client_company_data.pop('id', None) # Don't update ID
                for attr, value in client_company_data.items():
                    setattr(client_instance, attr, value)
                client_instance.save()
            else:
                # Create new client and link it
                client_instance = ProjectBusinessAddress.objects.create(**client_company_data)
                instance.client_company = client_instance
        
        instance.save()

        if items_data is not None:
            # SYNC ITEMS: Update existing, Create new, Delete omitted
            incoming_item_ids = [item_data.get('id') for item_data in items_data if item_data.get('id')]
            instance.items.exclude(id__in=incoming_item_ids).delete()
            
            existing_items = {i.id: i for i in instance.items.all()}
            for item_data in items_data:
                i_id = item_data.get('id')
                item_data.pop('invoice', None)
                if i_id and i_id in existing_items:
                    # Update
                    item_obj = existing_items[i_id]
                    for attr, value in item_data.items():
                        setattr(item_obj, attr, value)
                    item_obj.save()
                else:
                    # Create
                    InvoiceItem.objects.create(invoice=instance, **item_data)

        # --- Payments are now handled via dedicated nested endpoints ---
        # No more complex "Absolute Synchronization" inside the Invoice serializer.
        # This prevents accidental deletion of payment history.
        if payments_data is not None:
            # Optional: Allow read-only or simple display if needed, 
            # but don't perform CRUD here anymore.
            pass

        update_invoice_totals(instance)
        return instance



class ActivityExceedCommentSerializer(serializers.ModelSerializer):
    commenter_name = serializers.ReadOnlyField(source='commented_by.username')
    class Meta:
        model = ActivityExceedComment
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'

class EmployeeLeaveSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    project_names = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeLeave
        fields = '__all__'

    def get_employee_name(self, obj):
        if obj.employee.first_name or obj.employee.last_name:
            return f"{obj.employee.first_name} {obj.employee.last_name}".strip()
        return obj.employee.username

    def get_project_names(self, obj):
        from .models import ProjectTeamMember
        memberships = ProjectTeamMember.objects.filter(
            employee=obj.employee
        ).select_related('project')
        
        projects = []
        for m in memberships:
            # We assume project model has a name field. Sometimes it's in project_base_informations.
            # Let's handle both cases just in case, but usually m.project.name works if defined.
            if hasattr(m.project, 'name') and m.project.name:
                projects.append(m.project.name)
            elif hasattr(m.project, 'project_base_informations'):
                base_info = m.project.project_base_informations.first()
                if base_info and base_info.name:
                    projects.append(base_info.name)
        
        return ", ".join(set(projects)) if projects else "No Project"

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'

class CompanyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyProfile
        fields = '__all__'

class EmployeeSalarySummarySerializer(serializers.ModelSerializer):
    total_paid_amount = serializers.SerializerMethodField()
    total_unpaid_amount = serializers.SerializerMethodField()
    record_count = serializers.SerializerMethodField()
    paid_count = serializers.SerializerMethodField()
    unpaid_count = serializers.SerializerMethodField()
    last_payment_date = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'total_paid_amount', 'total_unpaid_amount', 'record_count', 'paid_count', 'unpaid_count', 'last_payment_date']

    def get_total_paid_amount(self, obj):
        from .models import Salary
        return obj.salaries.filter(status='Paid').aggregate(total=models.Sum('total_salary'))['total'] or 0

    def get_total_unpaid_amount(self, obj):
        from .models import Salary
        return obj.salaries.filter(status='Unpaid').aggregate(total=models.Sum('total_salary'))['total'] or 0

    def get_record_count(self, obj):
        return obj.salaries.count()

    def get_paid_count(self, obj):
        return obj.salaries.filter(status='Paid').count()

    def get_unpaid_count(self, obj):
        return obj.salaries.filter(status='Unpaid').count()

    def get_last_payment_date(self, obj):
        last_salary = obj.salaries.order_by('-end_date').first()
        return last_salary.end_date if last_salary else None

class SalarySerializer(serializers.ModelSerializer):
    employee_name = serializers.ReadOnlyField(source='employee.username')
    absent_days = serializers.SerializerMethodField()

    def get_absent_days(self, obj):
        return float(obj.working_days) - float(obj.present_days)
    
    class Meta:
        model = Salary
        fields = [
            'id', 'employee', 'employee_name', 'start_date', 'end_date', 
            'basic', 'working_days', 'present_days', 'absent_days', 'overtime_pay', 
            'late_deduction', 'bonus', 'advance', 'deductions', 
            'total_salary', 'gross_salary', 'total_deductions', 'net_salary',
            'status', 'is_locked', 'created_at', 'updated_at'
        ]
        read_only_fields = ['working_days', 'present_days', 'total_salary', 'overtime_pay', 'late_deduction', 'gross_salary', 'total_deductions', 'net_salary', 'is_locked', 'created_at', 'updated_at']

class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    project_names = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = '__all__'

    def get_employee_name(self, obj):
        if obj.employee.first_name or obj.employee.last_name:
            return f"{obj.employee.first_name} {obj.employee.last_name}".strip()
        return obj.employee.username

    def get_project_names(self, obj):
        from .models import ProjectTeamMember
        memberships = ProjectTeamMember.objects.filter(
            employee=obj.employee
        ).select_related('project')
        
        projects = []
        for m in memberships:
            if m.project and m.project.name:
                projects.append(m.project.name)
        
        return ", ".join(set(projects)) if projects else "No Project"

    def validate(self, attrs):
        request = self.context.get('request')
        if request and 'approval_status' in attrs:
            if not request.user.has_perm('djangosimplemissionapp.approve_attendance'):
                attrs.pop('approval_status', None)
        return attrs

class UserSalarySerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    next_salary_day = serializers.SerializerMethodField()

    def get_next_salary_day(self, obj):
        """Calculate next salary day based on joining_date and working_days cycle"""
        from .models import get_cycle_for_date
        from django.utils import timezone
        
        if not obj.joining_date:
            return None
        
        today = timezone.now().date()
        working_days = obj.working_days or 26
        
        start_date, end_date = get_cycle_for_date(obj.joining_date, today, working_days)
        
        if end_date:
            return end_date.isoformat()
        return None

    class Meta:
        model = UserSalary
        fields = ['id', 'user', 'username', 'base_salary', 'working_days', 'joining_date', 'effective_date', 'next_salary_day', 'created_at', 'updated_at']


class SalaryIncrementSerializer(serializers.ModelSerializer):
    employee_name = serializers.ReadOnlyField(source='employee.username')
    created_by_name = serializers.ReadOnlyField(source='created_by.username')

    class Meta:
        model = SalaryIncrement
        fields = [
            'id', 'employee', 'employee_name', 'old_salary', 'increment_amount', 
            'new_salary', 'effective_date', 'remarks', 'created_by', 'created_by_name',
            'created_at'
        ]
        read_only_fields = ['created_at']

class EmployeeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Employee
        fields = '__all__'

class OtherIncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherIncome
        fields = '__all__'

class OtherExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherExpense
        fields = '__all__'


class ProjectTeamSerializer(serializers.ModelSerializer):
    members = ProjectTeamMemberSerializer(many=True, required=False)
    team_detail = TeamSerializer(source='team', read_only=True)
    team = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = ProjectTeam
        fields = ['id', 'project', 'team', 'team_detail', 'members',
                  'start_date', 'end_date', 'deadline', 'actual_end_date', 'status', 'invoice_status', 'payment_status', 'cost', 'description', 'created_at', 'updated_at']
        extra_kwargs = {
            'id': {'read_only': False, 'required': False, 'allow_null': True},
            'project': {'required': False, 'allow_null': True},
        }

    def create(self, validated_data):
        members_data = validated_data.pop('members', [])
        validated_data.pop('id', None)
        project_team = ProjectTeam.objects.create(**validated_data)
        for member_data in members_data:
            member_data.pop('id', None)
            # Always inject the project so target_work_percentage lookup works
            member_data['project'] = project_team.project
            member = ProjectTeamMember.objects.create(**member_data)
            project_team.members.add(member)
        return project_team

    def update(self, instance, validated_data):
        members_data = validated_data.pop('members', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if members_data is not None:
            instance.members.all().delete()
            for member_data in members_data:
                member_data.pop('id', None)
                # Always inject the project so target_work_percentage lookup works
                member_data['project'] = instance.project
                member = ProjectTeamMember.objects.create(**member_data)
                instance.members.add(member)
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user:
            user = request.user
            is_admin_or_sa = user.is_superuser
            if hasattr(user, 'has_role'):
                is_admin_or_sa = is_admin_or_sa or user.has_role('SuperAdmin') or user.has_role('Admin')
            
            if not is_admin_or_sa:
                if 'members' in representation:
                    has_member_perm = (
                        user.has_perm('djangosimplemissionapp.view_projectteammember') or
                        user.has_perm('djangosimplemissionapp.all_projectteammember') or
                        user.has_perm('djangosimplemissionapp.own_projectteammember')
                    )
                    if not has_member_perm:
                        representation.pop('members', None)
                    elif not (user.has_perm('djangosimplemissionapp.view_projectteammember') or user.has_perm('djangosimplemissionapp.all_projectteammember')):
                        # Filter to only the user's own team members
                        representation['members'] = [m for m in representation.get('members', []) if m.get('employee') == user.id]
        return representation


class ProjectServiceTeamSerializer(serializers.ModelSerializer):
    team_detail = TeamSerializer(source='team', read_only=True)
    team = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = ProjectServiceTeam
        fields = ['id', 'service', 'team', 'team_detail', 'start_date', 'end_date', 'deadline', 'actual_end_date', 'status']
        extra_kwargs = {
            'id': {'read_only': False, 'required': False, 'allow_null': True},
            'service': {'required': False, 'allow_null': True},
        }


class ProjectServiceMemberSerializer(serializers.ModelSerializer):
    employee_detail = UserSerializer(source='employee', read_only=True)
    employee = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = ProjectServiceMember
        fields = ['id', 'service', 'employee', 'employee_detail', 'role',
                  'allocated_days', 'actual_days', 'cost', 'start_date', 'end_date', 'status', 'notes']
        extra_kwargs = {
            'id': {'read_only': False, 'required': False, 'allow_null': True},
            'service': {'required': False, 'allow_null': True},
        }

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user:
            user = request.user
            is_admin_or_sa = user.is_superuser
            if hasattr(user, 'has_role'):
                is_admin_or_sa = is_admin_or_sa or user.has_role('SuperAdmin') or user.has_role('Admin')
            
            if not is_admin_or_sa:
                if instance.employee_id != user.id and not user.has_perm('djangosimplemissionapp.alldate_projectservicemember'):
                    representation.pop('start_date', None)
                    representation.pop('end_date', None)
                    representation.pop('allocated_days', None)
                    representation.pop('actual_days', None)
                    representation.pop('cost', None)
        return representation


class ProjectServiceSerializer(serializers.ModelSerializer):
    teams   = ProjectServiceTeamSerializer(many=True, required=False)
    members = ProjectServiceMemberSerializer(many=True, required=False)

    class Meta:
        model = ProjectService
        fields = ['id', 'project', 'client_address', 'name', 'description', 
                  'deadline', 'actual_end_date', 'status', 'invoice_status', 'payment_status', 'cost', 'created_at', 'teams', 'members']
        extra_kwargs = {
            'id': {'read_only': False, 'required': False, 'allow_null': True},
            'project': {'required': False, 'allow_null': True},
        }

    def create(self, validated_data):
        teams_data   = validated_data.pop('teams', [])
        members_data = validated_data.pop('members', [])
        validated_data.pop('id', None)
        validated_data.pop('project', None)
        service = ProjectService.objects.create(**validated_data)
        for t_data in teams_data:
            t_data.pop('id', None)
            t_data.pop('service', None)
            ProjectServiceTeam.objects.create(service=service, **t_data)
        for m_data in members_data:
            m_data.pop('id', None)
            m_data.pop('service', None)
            ProjectServiceMember.objects.create(service=service, **m_data)
        return service

    def update(self, instance, validated_data):
        teams_data   = validated_data.pop('teams', None)
        members_data = validated_data.pop('members', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if teams_data is not None:
            instance.teams.all().delete()
            for t_data in teams_data:
                t_data.pop('id', None)
                t_data.pop('service', None)
                ProjectServiceTeam.objects.create(service=instance, **t_data)
        if members_data is not None:
            instance.members.all().delete()
            for m_data in members_data:
                m_data.pop('id', None)
                m_data.pop('service', None)
                ProjectServiceMember.objects.create(service=instance, **m_data)
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user:
            user = request.user
            is_admin_or_sa = user.is_superuser
            if hasattr(user, 'has_role'):
                is_admin_or_sa = is_admin_or_sa or user.has_role('SuperAdmin') or user.has_role('Admin')
            
            if not is_admin_or_sa:
                if 'members' in representation:
                    has_member_perm = (
                        user.has_perm('djangosimplemissionapp.view_projectservicemember') or
                        user.has_perm('djangosimplemissionapp.all_projectservicemember') or
                        user.has_perm('djangosimplemissionapp.own_projectservicemember')
                    )
                    if not has_member_perm:
                        representation.pop('members', None)
                    elif not (user.has_perm('djangosimplemissionapp.view_projectservicemember') or user.has_perm('djangosimplemissionapp.all_projectservicemember')):
                        # Filter to only the user's own service members
                        representation['members'] = [m for m in representation.get('members', []) if m.get('employee') == user.id]
                if 'teams' in representation:
                    if not user.has_perm('djangosimplemissionapp.view_projectserviceteam') and not user.has_perm('djangosimplemissionapp.view_projectservice'):
                        representation.pop('teams', None)
        return representation


class ProjectSummarySerializer(serializers.ModelSerializer):
    total_invoiced = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    total_balance_due = serializers.SerializerMethodField()
    business_address_id = serializers.SerializerMethodField()
    legal_name = serializers.SerializerMethodField()
    invoice_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'name', 'total_invoiced', 'total_paid', 'total_balance_due', 'business_address_id', 'legal_name', 'invoice_count']

    def get_total_invoiced(self, obj):
        # Aggregate totals from all invoices linked to this project's business addresses
        # Note the plural 'projects' due to M2M relationship
        return Invoice.objects.filter(client_company__projects=obj).aggregate(total=models.Sum('total_amount'))['total'] or 0

    def get_total_paid(self, obj):
        return Invoice.objects.filter(client_company__projects=obj).aggregate(total=models.Sum('total_paid'))['total'] or 0

    def get_total_balance_due(self, obj):
        return Invoice.objects.filter(client_company__projects=obj).aggregate(total=models.Sum('balance_due'))['total'] or 0

    def get_business_address_id(self, obj):
        # Returns the ID of the first associated business address
        address = obj.project_business_addresses.first()
        return address.id if address else None

    def get_legal_name(self, obj):
        # Returns the legal name of the first associated business address
        address = obj.project_business_addresses.first()
        return address.legal_name if address else None

    def get_invoice_count(self, obj):
        # Returns the number of invoices linked to this project's business addresses
        return Invoice.objects.filter(client_company__projects=obj).count()


class ProjectSerializer(serializers.ModelSerializer):
    """
    Full nested CREATE / UPDATE for a Project.
    All related models now use ForeignKey (reverse relations) instead of M2M.
    """

    # Reverse FK nested fields
    project_base_informations  = ProjectBaseInformationSerializer(many=True, required=False)
    project_excutions          = ProjectExcutionSerializer(many=True, required=False)
    project_finances           = ProjectFinanceSerializer(many=True, required=False)
    project_domains            = ProjectDomainSerializer(many=True, required=False)
    project_servers            = ProjectServerSerializer(many=True, required=False)
    project_clients            = ProjectClientSerializer(many=True, required=False)
    project_teams              = ProjectTeamSerializer(many=True, required=False)
    project_team_members       = ProjectTeamMemberSerializer(many=True, required=False)
    services                   = ProjectServiceSerializer(many=True, required=False)
    project_documents          = ProjectDocumentSerializer(many=True, required=False)
    project_exbots             = ProjectExbotSerializer(many=True, required=False)

    # ManyToMany: Project Business Addresses
    project_business_addresses = ProjectBusinessAddressSerializer(many=True, required=False)


    # FK: write PK, read detail
    project_nature_detail = ProjectNatureSerializer(source='project_nature', read_only=True)
    project_nature = serializers.PrimaryKeyRelatedField(
        queryset=ProjectNature.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'status', 'created_at', 'updated_at',
            'project_nature', 'project_nature_detail',
            'project_business_addresses',
            'project_base_informations', 'project_excutions',
            'project_finances', 'project_domains', 'project_servers',
            'project_clients',
            'project_teams', 'project_team_members', 'services', 'project_documents', 'project_exbots',
        ]
        extra_kwargs = {'id': {'read_only': False, 'required': False, 'allow_null': True}}


    # ── Helper ──────────────────────────────────────────────────

    def _create_fk_children(self, model_class, project, data_list):
        """Create FK children, injecting `project` automatically."""
        for data in data_list:
            data.pop('id', None)
            data.pop('project', None)
            model_class.objects.create(project=project, **data)

    def _sync_fk_children(self, model_class, project, data_list):
        """Sync FK children: Update existing, Create new, Delete omitted."""
        if data_list is None:
            return
            
        existing_items = {obj.id: obj for obj in model_class.objects.filter(project=project)}
        incoming_ids = [item.get('id') for item in data_list if item.get('id')]
        
        # Delete items not in incoming list
        model_class.objects.filter(project=project).exclude(id__in=incoming_ids).delete()
        
        for data in data_list:
            item_id = data.get('id')
            data.pop('id', None)
            data.pop('project', None)
            if item_id and item_id in existing_items:
                # Update
                obj = existing_items[item_id]
                for attr, value in data.items():
                    setattr(obj, attr, value)
                obj.save()
            else:
                # Create
                model_class.objects.create(project=project, **data)

    # ── CREATE ──────────────────────────────────────────────────

    def create(self, validated_data):
        base_info_data   = validated_data.pop('project_base_informations', [])
        excution_data    = validated_data.pop('project_excutions', [])
        finance_data     = validated_data.pop('project_finances', [])
        domain_data      = validated_data.pop('project_domains', [])
        server_data      = validated_data.pop('project_servers', [])
        client_data      = validated_data.pop('project_clients', [])
        address_data     = validated_data.pop('project_business_addresses', [])
        team_data        = validated_data.pop('project_teams', [])
        team_member_data = validated_data.pop('project_team_members', [])
        service_data     = validated_data.pop('services', [])
        document_data    = validated_data.pop('project_documents', [])
        exbot_data       = validated_data.pop('project_exbots', [])

        project = Project.objects.create(**validated_data)

        # Handle Many-to-Many Business Addresses
        for addr_data in address_data:
            addr_id = addr_data.pop('id', None)
            if addr_id:
                address = ProjectBusinessAddress.objects.get(id=addr_id)
                # Update existing address
                for attr, value in addr_data.items():
                    setattr(address, attr, value)
                address.save()
            else:
                address = ProjectBusinessAddress.objects.create(**addr_data)
            address.projects.add(project)

        self._create_fk_children(ProjectBaseInformation, project, base_info_data)
        self._create_fk_children(ProjectExcution, project, excution_data)
        self._create_fk_children(ProjectFinance, project, finance_data)
        self._create_fk_children(ProjectClient, project, client_data)
        self._create_fk_children(ProjectTeamMember, project, team_member_data)
        self._create_fk_children(ProjectDocument, project, document_data)
        self._create_fk_children(ProjectExbot, project, exbot_data)


        for d_data in domain_data:
            d_data.pop('id', None)
            d_data.pop('project', None)
            provider_data = d_data.pop('provider', [])
            domain = ProjectDomain.objects.create(project=project, **d_data)
            for p_data in provider_data:
                p_data.pop('id', None)
                provider = DomainOrServerThirdPartyServiceProvider.objects.create(**p_data)
                domain.provider.add(provider)

        for s_data in server_data:
            s_data.pop('id', None)
            s_data.pop('project', None)
            provider_data = s_data.pop('provider', [])
            server = ProjectServer.objects.create(project=project, **s_data)
            for p_data in provider_data:
                p_data.pop('id', None)
                provider = DomainOrServerThirdPartyServiceProvider.objects.create(**p_data)
                server.provider.add(provider)

        for t_data in team_data:
            t_data.pop('id', None)
            t_data.pop('project', None)
            members_data = t_data.pop('members', [])
            pt = ProjectTeam.objects.create(project=project, **t_data)
            for m_data in members_data:
                m_data.pop('id', None)
                member = ProjectTeamMember.objects.create(**m_data)
                pt.members.add(member)

        for svc_data in service_data:
            svc_data.pop('id', None)
            svc_data.pop('project', None)
            svc_teams   = svc_data.pop('teams', [])
            svc_members = svc_data.pop('members', [])
            svc = ProjectService.objects.create(project=project, **svc_data)
            for st_data in svc_teams:
                st_data.pop('id', None)
                st_data.pop('service', None)
                ProjectServiceTeam.objects.create(service=svc, **st_data)
            for sm_data in svc_members:
                sm_data.pop('id', None)
                sm_data.pop('service', None)
                ProjectServiceMember.objects.create(service=svc, **sm_data)

        return project

    # ── UPDATE ──────────────────────────────────────────────────

    def update(self, instance, validated_data):
        base_info_data   = validated_data.pop('project_base_informations', None)
        excution_data    = validated_data.pop('project_excutions', None)
        finance_data     = validated_data.pop('project_finances', None)
        domain_data      = validated_data.pop('project_domains', None)
        server_data      = validated_data.pop('project_servers', None)
        client_data      = validated_data.pop('project_clients', None)
        address_data     = validated_data.pop('project_business_addresses', None)
        team_data        = validated_data.pop('project_teams', None)
        team_member_data = validated_data.pop('project_team_members', None)
        service_data     = validated_data.pop('services', None)
        document_data    = validated_data.pop('project_documents', None)
        exbot_data       = validated_data.pop('project_exbots', None)

        if address_data is not None:
            # Sync Many-to-Many addresses
            new_address_list = []
            for addr_data in address_data:
                addr_id = addr_data.pop('id', None)
                if addr_id:
                    address = ProjectBusinessAddress.objects.get(id=addr_id)
                    # Update fields if provided
                    for attr, value in addr_data.items():
                        setattr(address, attr, value)
                    address.save()
                else:
                    address = ProjectBusinessAddress.objects.create(**addr_data)
                new_address_list.append(address)
            
            # Use .set() to update the M2M relationship
            instance.project_business_addresses.set(new_address_list)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if base_info_data is not None:
            self._sync_fk_children(ProjectBaseInformation, instance, base_info_data)
        if excution_data is not None:
            self._sync_fk_children(ProjectExcution, instance, excution_data)
        if finance_data is not None:
            self._sync_fk_children(ProjectFinance, instance, finance_data)
        if client_data is not None:
            self._sync_fk_children(ProjectClient, instance, client_data)
        if team_member_data is not None:
            self._sync_fk_children(ProjectTeamMember, instance, team_member_data)
        if document_data is not None:
            self._sync_fk_children(ProjectDocument, instance, document_data)
        
        self._sync_fk_children(ProjectExbot, instance, exbot_data)

        if domain_data is not None:
            incoming_ids = [d.get('id') for d in domain_data if d.get('id')]
            instance.project_domains.exclude(id__in=incoming_ids).delete()
            existing_domains = {d.id: d for d in instance.project_domains.all()}

            for d_data in domain_data:
                d_id = d_data.get('id')
                d_data.pop('id', None)
                d_data.pop('project', None)
                provider_data = d_data.pop('provider', [])
                if d_id and d_id in existing_domains:
                    domain = existing_domains[d_id]
                    for attr, value in d_data.items(): setattr(domain, attr, value)
                    domain.save()
                else:
                    domain = ProjectDomain.objects.create(project=instance, **d_data)
                
                domain.provider.all().delete()
                for p_data in provider_data:
                    p_data.pop('id', None)
                    provider = DomainOrServerThirdPartyServiceProvider.objects.create(**p_data)
                    domain.provider.add(provider)

        if server_data is not None:
            incoming_ids = [s.get('id') for s in server_data if s.get('id')]
            instance.project_servers.exclude(id__in=incoming_ids).delete()
            existing_servers = {s.id: s for s in instance.project_servers.all()}

            for s_data in server_data:
                s_id = s_data.get('id')
                s_data.pop('id', None)
                s_data.pop('project', None)
                provider_data = s_data.pop('provider', [])
                if s_id and s_id in existing_servers:
                    server = existing_servers[s_id]
                    for attr, value in s_data.items(): setattr(server, attr, value)
                    server.save()
                else:
                    server = ProjectServer.objects.create(project=instance, **s_data)

                server.provider.all().delete()
                for p_data in provider_data:
                    p_data.pop('id', None)
                    provider = DomainOrServerThirdPartyServiceProvider.objects.create(**p_data)
                    server.provider.add(provider)

        if team_data is not None:
            incoming_ids = [t.get('id') for t in team_data if t.get('id')]
            instance.project_teams.exclude(id__in=incoming_ids).delete()
            existing_teams = {t.id: t for t in instance.project_teams.all()}

            for t_data in team_data:
                t_id = t_data.get('id')
                t_data.pop('id', None)
                t_data.pop('project', None)
                members_data = t_data.pop('members', [])
                if t_id and t_id in existing_teams:
                    pt = existing_teams[t_id]
                    for attr, value in t_data.items(): setattr(pt, attr, value)
                    pt.save()
                else:
                    pt = ProjectTeam.objects.create(project=instance, **t_data)

                pt.members.all().delete()
                for m_data in members_data:
                    m_data.pop('id', None)
                    member = ProjectTeamMember.objects.create(**m_data)
                    pt.members.add(member)

        if service_data is not None:
            incoming_ids = [s.get('id') for s in service_data if s.get('id')]
            instance.services.exclude(id__in=incoming_ids).delete()
            existing_svcs = {s.id: s for s in instance.services.all()}

            for svc_data in service_data:
                svc_id = svc_data.get('id')
                svc_data.pop('id', None)
                svc_data.pop('project', None)
                svc_teams = svc_data.pop('teams', [])
                svc_members = svc_data.pop('members', [])
                if svc_id and svc_id in existing_svcs:
                    svc = existing_svcs[svc_id]
                    for attr, value in svc_data.items(): setattr(svc, attr, value)
                    svc.save()
                else:
                    svc = ProjectService.objects.create(project=instance, **svc_data)

                svc.teams.all().delete()
                for st_data in svc_teams:
                    st_data.pop('id', None)
                    st_data.pop('service', None)
                    ProjectServiceTeam.objects.create(service=svc, **st_data)
                
                svc.members.all().delete()
                for sm_data in svc_members:
                    sm_data.pop('id', None)
                    sm_data.pop('service', None)
                    ProjectServiceMember.objects.create(service=svc, **sm_data)

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user:
            user = request.user
            is_admin_or_sa = user.is_superuser
            if hasattr(user, 'has_role'):
                is_admin_or_sa = is_admin_or_sa or user.has_role('SuperAdmin') or user.has_role('Admin')
            
            if not is_admin_or_sa:
                permissions_map = {
                    'project_nature': 'djangosimplemissionapp.view_projectnature',
                    'project_nature_detail': 'djangosimplemissionapp.view_projectnature',
                    'project_business_addresses': 'djangosimplemissionapp.view_projectbusinessaddress',
                    'project_base_informations': 'djangosimplemissionapp.view_projectbaseinformation',
                    'project_excutions': 'djangosimplemissionapp.view_projectexcution',
                    'project_finances': 'djangosimplemissionapp.view_projectfinance',
                    'project_domains': 'djangosimplemissionapp.view_projectdomain',
                    'project_servers': 'djangosimplemissionapp.view_projectserver',
                    'project_clients': 'djangosimplemissionapp.view_projectclient',
                    'project_teams': 'djangosimplemissionapp.view_projectteam',
                    'project_team_members': 'djangosimplemissionapp.view_projectteammember',
                    'services': 'djangosimplemissionapp.view_projectservice',
                    'project_documents': 'djangosimplemissionapp.view_projectdocument',
                    'project_exbots': 'djangosimplemissionapp.view_projectexbot',
                }
                
                for field, permission in permissions_map.items():
                    if field in representation:
                        if field == 'project_team_members':
                            has_permission = (
                                user.has_perm(permission) or 
                                user.has_perm('djangosimplemissionapp.all_projectteammember') or 
                                user.has_perm('djangosimplemissionapp.own_projectteammember')
                            )
                            if has_permission and not (user.has_perm(permission) or user.has_perm('djangosimplemissionapp.all_projectteammember')):
                                # Filter to only the user's own team members
                                if field in representation and isinstance(representation[field], list):
                                    representation[field] = [m for m in representation[field] if m.get('employee') == user.id]
                        elif field == 'services':
                            has_permission = (
                                user.has_perm(permission) or 
                                user.has_perm('djangosimplemissionapp.all_projectservicemember') or 
                                user.has_perm('djangosimplemissionapp.own_projectservicemember')
                            )
                        elif field == 'project_domains':
                            has_permission = (
                                user.has_perm(permission) or
                                user.has_perm('djangosimplemissionapp.viewnameonly_projectdomain')
                            )
                        elif field == 'project_servers':
                            has_permission = (
                                user.has_perm(permission) or
                                user.has_perm('djangosimplemissionapp.viewnameonly_projectserver')
                            )
                        else:
                            has_permission = user.has_perm(permission)
                            
                        if not has_permission:
                            representation.pop(field, None)
        return representation

class ScheduleSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.ReadOnlyField(source='assigned_to.username')
    assigned_role_name = serializers.ReadOnlyField(source='assigned_role.name')

    class Meta:
        model = Schedule
        fields = '__all__'

