from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Role, ProjectClient, ProjectBusinessAddress,
    DomainOrServerThirdPartyServiceProvider, ProjectDomain, ProjectServer,
    ProjectFinance, Team, ProjectTeam, ProjectNature, Project,
    ProjectBaseInformation, ProjectExcution, ProjectTeamMember,
    ProjectService, EmployeeDailyActivity, ActivityLog, Invoice,
    InvoiceItem, Payment, ActivityExceedComment, Notification,
    EmployeeLeave, Company, CompanyProfile, Salary, Attendance,
    Employee, OtherIncome, OtherExpense, UserSalary, ProjectExbot, Lead, FollowUp, SystemAuditLog,
    LoginUserDetails
)

# Custom UserAdmin to handle the custom User model
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'phone_number', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('phone_number', 'designation', 'role', 'is_phone_verified', 'is_email_verified')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('phone_number', 'designation', 'role', 'is_phone_verified', 'is_email_verified')}),
    )

# Register all models
admin.site.register(User, CustomUserAdmin)
admin.site.register(Role)
admin.site.register(ProjectClient)
admin.site.register(ProjectBusinessAddress)
admin.site.register(DomainOrServerThirdPartyServiceProvider)
admin.site.register(ProjectDomain)
admin.site.register(ProjectServer)
admin.site.register(ProjectExbot)
admin.site.register(ProjectFinance)
admin.site.register(Team)
admin.site.register(ProjectTeam)
admin.site.register(ProjectNature)
admin.site.register(Project)
admin.site.register(ProjectBaseInformation)
admin.site.register(ProjectExcution)
admin.site.register(ProjectTeamMember)
admin.site.register(ProjectService)
admin.site.register(EmployeeDailyActivity)
admin.site.register(ActivityLog)
admin.site.register(Invoice)
admin.site.register(InvoiceItem)
admin.site.register(Payment)
admin.site.register(ActivityExceedComment)
admin.site.register(Notification)
admin.site.register(EmployeeLeave)
admin.site.register(Company)
admin.site.register(CompanyProfile)
@admin.register(Salary)
class SalaryAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "start_date",
        "end_date",
        "working_days",
        "present_days",
        "basic",
        "total_salary",
        "status"
    )


admin.site.register(Attendance)
admin.site.register(Employee)
admin.site.register(OtherIncome)
admin.site.register(OtherExpense)
admin.site.register(UserSalary)

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'contact_person', 'lead_source', 'created_at')
    list_filter = ('lead_source',)
    search_fields = ('company_name', 'contact_person', 'contact_number')

@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ('lead', 'followup_date', 'interest_level', 'conversion_status', 'created_at')
    list_filter = ('followup_date', 'interest_level', 'conversion_status')

@admin.register(SystemAuditLog)
class SystemAuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'target', 'performed_by', 'created_at')
    search_fields = ('action', 'target', 'performed_by')
    list_filter = ('action', 'created_at')
    
    def has_add_permission(self, request):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(LoginUserDetails)
class LoginUserDetailsAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_time', 'logout_time', 'ip_address', 'device_type', 'login_status', 'is_suspicious')
    list_filter = ('login_status', 'device_type', 'is_suspicious', 'login_time')
    search_fields = ('user__username', 'ip_address', 'device_name', 'browser_name')
    readonly_fields = ('login_time', 'created_at', 'updated_at', 'session_duration')
    
    fieldsets = (
        ('User & Status', {'fields': ('user', 'login_status', 'is_suspicious')}),
        ('Timing', {'fields': ('login_time', 'logout_time', 'session_duration')}),
        ('Device Information', {'fields': ('device_type', 'device_name', 'browser_name', 'browser_version', 'os_name', 'os_version')}),
        ('Network', {'fields': ('ip_address',)}),
        ('Additional Info', {'fields': ('user_agent', 'notes')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
