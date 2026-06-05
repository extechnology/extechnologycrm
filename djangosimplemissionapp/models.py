from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, Permission
from decimal import Decimal
from django.utils import timezone
from django.db.models.signals import post_save, post_delete ,m2m_changed
from django.dispatch import receiver
from django.db.models import Sum, Count
import calendar
from datetime import timedelta

class UserManager(BaseUserManager):
    def create_user(self, email, username, phone_number=None, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        if not username:
            raise ValueError('The Username field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, phone_number=None, password=None, **extra_fields):

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')

        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        user = self.create_user(
            email=email,
            username=username,
            phone_number=phone_number,
            password=password,
            **extra_fields
        )

        # Assign SuperAdmin role
        superadmin_role, _ = Role.objects.get_or_create(name='SuperAdmin')
        user.role = superadmin_role
        user.save()
        # user.sync_permissions() # This might be deprecated, removing for now if not defined

        return user

class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    permissions = models.ManyToManyField(Permission, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class User(AbstractUser):

    email = models.EmailField(unique=True, default="example@example.com")
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)
    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    designation = models.CharField(max_length=100, blank=True, null=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    token_version = models.IntegerField(default=1)
    objects = UserManager()
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']  # Keep empty if username is login field

    class Meta:
        permissions = [
            ("view_all_employee_performance", "Can view all employee performance"),
            ("view_own_employee_performance", "Can view own employee performance"),
            ("view_all_leads", "Can view all leads"),
            ("view_own_leads", "Can view own leads"),
            ("viewall_user", "Can view all user details"),
            ("viewown_user", "Can view own user details"),
        ]

    def __str__(self):
        return self.username

    @property
    def role_names(self):
        names = []
        if self.role and self.role.name:
            names.append(self.role.name)
        if self.is_superuser and 'SuperAdmin' not in names:
            names.append('SuperAdmin')
        return names

    def has_role(self, role_name):
        if self.is_superuser:
            return True
        return self.role.name.upper() == role_name.upper() if self.role else False

    def has_any_role(self, roles_list):
        if self.is_superuser:
            return True
        if not self.role:
            return False
        roles_upper = [r.upper() for r in roles_list]
        return self.role.name.upper() in roles_upper

    def has_perm(self, perm, obj=None):
        if self.is_superuser:
            return True
        if self.role:
            # Check if perm is in role permissions (e.g. 'app.codename' or just 'codename')
            codename = perm.split('.')[-1]
            if self.role.permissions.filter(codename=codename).exists():
                return True
        return super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        if self.is_superuser:
            return True
        if self.role:
            if self.role.permissions.filter(content_type__app_label=app_label).exists():
                return True
        return super().has_module_perms(app_label)

    @property
    def is_admin(self):
        return self.is_superuser or self.has_any_role(['Admin', 'SuperAdmin'])

    @property
    def is_billing(self):
        return self.is_superuser or self.has_any_role(['Billing', 'SuperAdmin'])

    @property
    def is_teamhead(self):
        return self.is_superuser or self.has_role('TeamHead')

    @property
    def is_developer(self):
        return self.is_superuser or self.has_role('Developer')

    def sync_permissions(self):
        is_super = False
        is_staff = False
        if self.role:
            role_name = self.role.name.upper()
            if role_name == 'SUPERADMIN':
                is_super = True
                is_staff = True
            elif role_name in ['ADMIN', 'BILLING']:
                is_staff = True
                
        # Use update() to bypass signals and avoid infinite recursion
        User.objects.filter(id=self.id).update(
            is_superuser=is_super,
            is_staff=is_staff
        )

@receiver(post_save, sender=User)
def update_user_permissions(sender, instance, created, **kwargs):
    if not created:
        instance.sync_permissions()

class ProjectClient(models.Model):
    project  = models.ForeignKey("Project", on_delete=models.CASCADE, related_name='project_clients', null=True, blank=True)
    company_name = models.CharField(max_length=255, null=True,blank=True)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15,blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name or "Unnamed Client"

class ProjectBusinessAddress(models.Model):
    # Changed to ManyToMany to allow full sharing flexibility
    projects = models.ManyToManyField("Project", related_name='project_business_addresses', blank=True)
    gst_number = models.CharField(max_length=20, blank=True, null=True)
    pan_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15,blank=True, null=True)
    legal_name = models.CharField(max_length=255, blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    attention_name = models.CharField(max_length=255, blank=True, null=True)
    unit_or_floor = models.CharField(max_length=255, blank=True, null=True)
    building_name = models.CharField(max_length=255,blank=True, null=True)
    plot_number = models.CharField(max_length=100, blank=True, null=True)
    street_name = models.CharField(max_length=255,blank=True, null=True)
    landmark = models.CharField(max_length=255,blank=True, null=True)
    locality = models.CharField(max_length=255,blank=True, null=True)
    city = models.CharField(max_length=255,blank=True, null=True)
    district = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=255,blank=True, null=True)
    pin_code = models.CharField(max_length=6,blank=True, null=True)
    country = models.CharField(max_length=100, default="India",blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.legal_name or 'Business'} - {self.city or 'Unnamed City'}"

class ClientAdvance(models.Model):
    client = models.ForeignKey(
        ProjectBusinessAddress,
        on_delete=models.CASCADE,
        related_name="advances"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    advance_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    remaining_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    note = models.TextField(blank=True, null=True)
    initial_usage = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_manual = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client} - {self.amount}"

class DomainOrServerThirdPartyServiceProvider(models.Model):
    company_name = models.CharField(max_length=200, blank=True, null=True)
    contact_person = models.CharField(max_length=200, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name or "Provider"
class ProjectDomain(models.Model):
    ACCRUED_BY_CHOICES = (
        ('Extechnology', 'Extechnology'),
        ('Client', 'Client'),
        ('Third Party', 'Third Party'),
    )
    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Pending', 'Pending'),
        ('Expired', 'Expired'),
    )
    INVOICE_STATUS_CHOICES = (
        ('NOT_INVOICED', 'Not Invoiced'),
        ('INVOICED', 'Invoiced'),
    )
    project  = models.ForeignKey("Project", on_delete=models.CASCADE, related_name='project_domains', null=True, blank=True)
    client_address = models.ForeignKey("ProjectBusinessAddress", on_delete=models.SET_NULL, null=True, blank=True, related_name='domains')
    name = models.CharField(max_length=200, blank=True, null=True)
    accrued_by = models.CharField(max_length=50, choices=ACCRUED_BY_CHOICES, default='Extechnology')
    provider = models.ManyToManyField(DomainOrServerThirdPartyServiceProvider, blank=True, related_name='domains')
    purchased_from = models.CharField(max_length=200, blank=True, null=True)
    purchase_date = models.DateField(null=True, blank=True)
    expiration_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending', blank=True, null=True)
    invoice_status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default='NOT_INVOICED')
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    payment_status = models.CharField(
        max_length=20,
        choices=[('PAID', 'Paid'), ('UNPAID', 'Unpaid')],
        default='UNPAID'
    )

    def save(self, *args, **kwargs):
        from django.utils import timezone
        today = timezone.now().date()
        
        if not self.purchase_date and not self.expiration_date:
            self.status = 'Pending'
        elif self.expiration_date:
            if self.expiration_date < today:
                self.status = 'Expired'
            else:
                self.status = 'Active'
                
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or "Unnamed Domain"

    class Meta:
        permissions = [
            ("view_domain_stats", "Can view domain analytics and stats"),
            ("viewnameonly_projectdomain", "can view "),
            ("viewfinancials_projectdomain", "Can view financial data of domains"),
            ("viewdates_projectdomain", "Can view purchase/expiry dates of domains"),
        ]

class ProjectServer(models.Model):
    ACCRUED_BY_CHOICES = (
        ('Extechnology', 'Extechnology'),
        ('Client', 'Client'),
        ('Third Party', 'Third Party'),
    )
    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Pending', 'Pending'),
        ('Expired', 'Expired'),
    )
    INVOICE_STATUS_CHOICES = (
        ('NOT_INVOICED', 'Not Invoiced'),
        ('INVOICED', 'Invoiced'),
    )
    project  = models.ForeignKey("Project", on_delete=models.CASCADE, related_name='project_servers', null=True, blank=True)
    client_address = models.ForeignKey("ProjectBusinessAddress", on_delete=models.SET_NULL, null=True, blank=True, related_name='servers')
    server_type = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., VPS, Shared, Dedicated")
    name = models.CharField(max_length=200, blank=True, null=True, help_text="Hosting Provider Name")
    accrued_by = models.CharField(max_length=50, choices=ACCRUED_BY_CHOICES, default='Extechnology')
    provider = models.ManyToManyField(DomainOrServerThirdPartyServiceProvider, blank=True, related_name='servers')
    purchased_from = models.CharField(max_length=200, blank=True, null=True)
    purchase_date = models.DateField(null=True, blank=True)
    expiration_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending', blank=True, null=True)
    invoice_status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default='NOT_INVOICED')
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    payment_status = models.CharField(
        max_length=20,
        choices=[('PAID', 'Paid'), ('UNPAID', 'Unpaid')],
        default='UNPAID'
    )

    def save(self, *args, **kwargs):
        from django.utils import timezone
        today = timezone.now().date()
        
        if not self.purchase_date and not self.expiration_date:
            self.status = 'Pending'
        elif self.expiration_date:
            if self.expiration_date < today:
                self.status = 'Expired'
            else:
                self.status = 'Active'
                
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.server_type} - {self.name}" or "Unnamed Server"

    class Meta:
        permissions = [
            ("view_server_stats", "Can view server analytics and stats"),
            ("viewnameonly_projectserver", "can view "),
            ("viewfinancials_projectserver", "Can view financial data of servers"),
            ("viewdates_projectserver", "Can view purchase/expiry dates of servers"),
        ]

class ProjectExbot(models.Model):
    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Pending', 'Pending'),
        ('Expired', 'Expired'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('PAID', 'Paid'),
        ('UNPAID', 'Unpaid'),
    )
    INVOICE_STATUS_CHOICES = (
        ('NOT_INVOICED', 'Not Invoiced'),
        ('INVOICED', 'Invoiced'),
    )
    project = models.ForeignKey("Project", on_delete=models.CASCADE, related_name='project_exbots', null=True, blank=True)
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    plan_category = models.CharField(max_length=100, blank=True, null=True)
    plan_active_date = models.DateField(null=True, blank=True)
    plan_deactive_date = models.DateField(null=True, blank=True)
    plan_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='UNPAID')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    invoice_status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default='NOT_INVOICED')
    description = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        from django.utils import timezone
        today = timezone.now().date()
        
        if not self.plan_active_date and not self.plan_deactive_date:
            self.status = 'Pending'
        elif self.plan_deactive_date:
            if self.plan_deactive_date < today:
                self.status = 'Expired'
            else:
                self.status = 'Active'
                
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.whatsapp_number} - {self.plan_category}"

    class Meta:
        permissions = [
            ("view_exbot_stats", "Can view exbot analytics and stats"),
            ("viewfinancials_projectexbot", "Can view financial data of exbots"),
            ("viewdates_projectexbot", "Can view active/deactive dates of exbots"),
        ]

class ProjectFinance(models.Model):
    INVOICE_STATUS_CHOICES = (
        ('NOT_INVOICED', 'Not Invoiced'),
        ('INVOICED', 'Invoiced'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('PAID', 'Paid'),
        ('UNPAID', 'Unpaid'),
    )
    project  = models.ForeignKey("Project", on_delete=models.CASCADE, related_name='project_finances', null=True, blank=True)
    project_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Fixed Project Cost (Budget)")
    invoice_status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default='NOT_INVOICED')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='UNPAID')

    def __str__(self):
        return f"Finance Record {self.id}"

class Team(models.Model):
    name = models.CharField(max_length=200, blank=True, null=True)
    team_lead = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='led_teams')
    members = models.ManyToManyField(User, related_name='teams',blank=True,)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        permissions = [
            ("view_teamperformance", "Can view team performance analytics"),
            ("view_all_team_performance", "Can view performance of all teams"),
            ("view_own_team_performance", "Can view performance of own team only"),
            ("viewown_team", "Can view own team details "),
            ("viewall_team", "Can view all team details"),
        ]


class ProjectTeam(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Progressing', 'Progressing'),
        ('Completed', 'Completed'),
    ]
    project  = models.ForeignKey("Project", on_delete=models.CASCADE, related_name='project_teams', null=True, blank=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='project_allocations',blank=True, null=True)
    members = models.ManyToManyField('ProjectTeamMember', related_name='project_allocations')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    INVOICE_STATUS_CHOICES = (
        ('NOT_INVOICED', 'Not Invoiced'),
        ('INVOICED', 'Invoiced'),
    )
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    invoice_status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default='NOT_INVOICED')
    payment_status = models.CharField(
        max_length=20,
        choices=[('PAID', 'Paid'), ('UNPAID', 'Unpaid')],
        default='UNPAID'
    )
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

   

    def __str__(self):
        return f"Team Allocation: {self.team.name if self.team else 'No Team'}"
class ProjectNature(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Project(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Progressing', 'Progressing'),
        ('Completed', 'Completed'),
    ]
    name = models.CharField(max_length=200,blank=True, null=True)
    # business_address FK removed in favor of M2M on ProjectBusinessAddress
    project_nature = models.ForeignKey(ProjectNature, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    description = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        permissions = [
            ("view_analytics",    "Can view analytical dashboard"),
            ("view_projectstats", "Can view project analytics and stats"),
            ("viewprojectfinancestats_analytics", "Can view financial data of projects")
        ]
 
class ProjectDocument(models.Model):
    project = models.ForeignKey(
        "Project", 
        on_delete=models.CASCADE, 
        related_name="project_documents", 
        null=True, 
        blank=True
    )
    name = models.CharField(max_length=255)
    document = models.FileField(upload_to='project_documents/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.project.name if self.project else 'No Project'}"

class ProjectBaseInformation(models.Model):
    project  = models.ForeignKey("Project", on_delete=models.CASCADE, related_name='project_base_informations', null=True, blank=True)
    project_approach_date = models.DateField(null=True, blank=True)
    name = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    creator_name = models.CharField(max_length=200, blank=True, null=True)
    creator_designation = models.CharField(max_length=200, blank=True, null=True)

class ProjectExcution(models.Model):
    project  = models.ForeignKey("Project", on_delete=models.CASCADE, related_name='project_excutions', null=True, blank=True)
    work_assigned_date = models.DateField(null=True, blank=True)
    assigned_delivery_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    confirmed_end_date = models.DateField(help_text="Deadline", null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    

class ProjectTeamMember(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Progressing', 'Progressing'),
        ('Completed', 'Completed'),
    ]
    project  = models.ForeignKey("Project", on_delete=models.CASCADE, related_name='project_team_members', null=True, blank=True)
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="project_team_memberships")
    role = models.CharField(max_length=100, blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Employee Cost for the project")
    allocated_days = models.IntegerField(default=0, help_text="Days Allowed")
    actual_days_spent = models.IntegerField(null=True, blank=True, default=0, help_text="Actually Spent Days")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True, help_text="End Date")
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending', help_text="Task Status")
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.employee.username} - {self.role}"

    class Meta: 
        permissions = [
            ("all_projectteammember", "Can view all project team members"),
            ("own_projectteammember", "Can view own project team member assignments"),
            ("alldate_projectteammember", "Can view all project team member dates")
        ]


class ProjectService(models.Model):

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Progressing', 'Progressing'),
        ('Completed', 'Completed'),
    ]
    project = models.ForeignKey(
        "Project",
        on_delete=models.CASCADE,
        related_name="services",
        null=True,
        blank=True
    )

    client_address = models.ForeignKey(
        "ProjectBusinessAddress",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="services"
    )

    name = models.CharField(max_length=200, blank=True, null=True)

    description = models.TextField(blank=True, null=True)

    deadline = models.DateField(null=True, blank=True)

    actual_end_date = models.DateField(null=True, blank=True)

    INVOICE_STATUS_CHOICES = (
        ('NOT_INVOICED', 'Not Invoiced'),
        ('INVOICED', 'Invoiced'),
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default="Pending"
    )
    invoice_status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default='NOT_INVOICED')
    payment_status = models.CharField(
        max_length=20,
        choices=[('PAID', 'Paid'), ('UNPAID', 'Unpaid')],
        default='UNPAID'
    )
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.project} - {self.name}"

class ProjectServiceTeam(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Progressing', 'Progressing'),
        ('Completed', 'Completed'),
    ]

    service = models.ForeignKey(
        ProjectService,
        on_delete=models.CASCADE,
        related_name="teams"
    )

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE
    )

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"{self.service.name} - {self.team.name if self.team else 'No Team'}"
class ProjectServiceMember(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Progressing', 'Progressing'),
        ('Completed', 'Completed'),
    ]
    service = models.ForeignKey(
        ProjectService,
        on_delete=models.CASCADE,
        related_name="members"
    )

    employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    role = models.CharField(max_length=100)

    allocated_days = models.IntegerField(default=0)

    actual_days = models.IntegerField(default=0)

    cost = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.employee.username} - {self.service.name}"

    class Meta:
        permissions = [
            ("all_projectservicemember", "Can view all project service members"),
            ("own_projectservicemember", "Can view own project service member assignments"),
            ("alldate_projectservicemember", "Can view all project service member dates")

        ]



class EmployeeDailyActivity(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_activities')
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='daily_activities'
    )
    project = models.ForeignKey(
        "Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='daily_activities'
    )
    project_service = models.ForeignKey(
        "ProjectService",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employee_activities'
    )
    description = models.TextField()
    hours_spent = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0
    )
    date = models.DateField()
    pending_work_percentage = models.IntegerField(default=0)
    target_work_percentage = models.IntegerField(default=0)
    is_timeline_exceeded = models.BooleanField(default=False)
    delay_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name_plural = "Employee Daily Activities"
        permissions = [
            ("view_all_activities", "Can view all employee daily activities"),
            ("view_own_activities", "Can view own daily activities"),
            ("viewmeandprojectmember_employeedailyactivity", "Can view activities of self, project team members, and service team members"),
        ]  
   

    def __str__(self):
        return f"{self.employee.username} - {self.date}"
 
class ActivityLog(models.Model):
    activity = models.ForeignKey(EmployeeDailyActivity, on_delete=models.CASCADE, related_name='logs')
    description = models.TextField()
    timestamp = models.TimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Log for {self.activity} at {self.timestamp}"

class Invoice(models.Model):

    STATUS_CHOICES = [
        ('UNPAID', 'Unpaid'),
        ('PARTIAL', 'Partial'),
        ('PAID', 'Paid'),
    ]

    client_company = models.ForeignKey(
        ProjectBusinessAddress,
        on_delete=models.SET_NULL,
        null=True,
        related_name="invoices"
    )

    invoice_number = models.CharField(max_length=50, unique=True,blank=True,null=True)
    invoice_date = models.DateField(auto_now_add=True)

    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance_due = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNPAID')

    due_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            from django.utils import timezone
            date_str = timezone.now().strftime('%Y%m%d')
            # Get the count of invoices created today to generate a sequence
            last_invoice = Invoice.objects.filter(invoice_number__startswith=f'INV-{date_str}-').order_by('invoice_number').last()
            
            if last_invoice and last_invoice.invoice_number:
                try:
                    last_seq = int(last_invoice.invoice_number.split('-')[-1])
                    new_seq = last_seq + 1
                except (ValueError, IndexError):
                    new_seq = 1
            else:
                new_seq = 1
            
            self.invoice_number = f'INV-{date_str}-{new_seq:04d}'
            
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            # Ledger component decommissioned per user request. 
            pass

        self.update_related_payment_status()

    def update_related_payment_status(self):
        if self.status != "PAID":
            return
        for item in self.items.all():
            if item.project_domain:
                item.project_domain.payment_status = "PAID"
                item.project_domain.save(update_fields=["payment_status"])
            if item.project_service:
                item.project_service.payment_status = "PAID"
                item.project_service.save(update_fields=["payment_status"])
            if item.project_server:
                item.project_server.payment_status = "PAID"
                item.project_server.save(update_fields=["payment_status"])
            if (pt := item.project_team):
                pt.payment_status = "PAID"
                pt.save(update_fields=["payment_status"])
            if item.project_exbot:
                item.project_exbot.payment_status = "PAID"
                item.project_exbot.save(update_fields=["payment_status"])
            if item.project_finance:
                item.project_finance.payment_status = "PAID"
                item.project_finance.save(update_fields=["payment_status"])

    def update_totals(self):
        """
        Recalculates invoice totals and paid amounts.
        Ensures ERP-standard: total_paid <= total_amount and balance_due >= 0.
        """
        from decimal import Decimal
        from django.db.models import Sum

        subtotal = self.items.aggregate(total=Sum("total_price"))["total"] or Decimal("0.00")
        self.subtotal = Decimal(str(subtotal))
        self.tax_amount = (self.subtotal * self.tax_rate) / 100
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        
        # Calculate actual paid from all payments
        actual_paid_total = self.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        
        # ERP Logic: Invoice only shows paid up to its own total. Excess went to Advances.
        self.total_paid = min(Decimal(str(actual_paid_total)), self.total_amount)
        self.balance_due = max(Decimal("0.00"), self.total_amount - self.total_paid)
        
        if self.balance_due == 0 and self.total_amount > 0:
            self.status = "PAID"
        elif self.total_paid > 0:
            self.status = "PARTIAL"
        else:
            self.status = "UNPAID"
            
        self.save(update_fields=["subtotal", "tax_amount", "total_amount", "total_paid", "balance_due", "status"])

    def __str__(self):
        return self.invoice_number or f"Invoice {self.id}"
class InvoiceItem(models.Model):

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items",
        null=True,
        blank=True
    )

    # LINK SERVICE
    project_service = models.ForeignKey(
        "ProjectService",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_items"
    )

    # LINK DOMAIN
    project_domain = models.ForeignKey(
        "ProjectDomain",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_items"
    )

    # LINK SERVER
    project_server = models.ForeignKey(
        "ProjectServer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_items"
    )

    # LINK TEAM
    project_team = models.ForeignKey(
        "ProjectTeam",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_items"
    )

    # LINK EXBOT
    project_exbot = models.ForeignKey(
        "ProjectExbot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_items"
    )

    # LINK FINANCE
    project_finance = models.ForeignKey(
        "ProjectFinance",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_items"
    )

    service_type = models.CharField(max_length=100,blank=True,null=True)

    description = models.TextField(blank=True,null=True)

    rate = models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True)

    quantity = models.PositiveIntegerField(default=1,blank=True,null=True)

    total_price = models.DecimalField(max_digits=12, decimal_places=2,blank=True,null=True)

    purchase_date = models.DateField(blank=True, null=True)
    expairy_date = models.DateField(blank=True, null=True)

    def save(self, *args, **kwargs):
        self.total_price = (self.rate or Decimal("0.00")) * (self.quantity or 0)
        super().save(*args, **kwargs)
        
        # Automate Invoice Status
        if self.project_domain:
            self.project_domain.invoice_status = 'INVOICED'
            self.project_domain.save(update_fields=['invoice_status'])
        if self.project_server:
            self.project_server.invoice_status = 'INVOICED'
            self.project_server.save(update_fields=['invoice_status'])
        if self.project_exbot:
            self.project_exbot.invoice_status = 'INVOICED'
            self.project_exbot.save(update_fields=['invoice_status'])

        if self.project_service:
            self.project_service.invoice_status = 'INVOICED'
            self.project_service.save(update_fields=['invoice_status'])

        if self.project_team:
            self.project_team.invoice_status = 'INVOICED'
            self.project_team.save(update_fields=['invoice_status'])

        if self.project_finance:
            self.project_finance.invoice_status = 'INVOICED'
            self.project_finance.save(update_fields=['invoice_status'])

        if self.invoice:
            self.invoice.update_totals()

    def __str__(self):
        return self.service_type or f"Item {self.id}"
class Payment(models.Model):

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payments",
        null=True,
        blank=True
    )
    advance_applied = models.ForeignKey(
        "ClientAdvance",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_applications"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    payment_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # Save the record first to get a PK
        super().save(*args, **kwargs)
        
        # 1. If it's a new payment, run the full accounting logic (Ledger/Advance)
        if is_new:
            from .services import process_payment_accounting
            process_payment_accounting(self)
        else:
            # 2. If it's an update, at least refresh the Invoice totals
            if self.invoice:
                self.invoice.update_totals()

    def __str__(self):
        return f"Payment {self.amount}"

@receiver(post_save, sender=Payment)
def handle_payment_save(sender, instance, **kwargs):
    """Trigger advance synchronization on payment change."""
    if instance.invoice and instance.invoice.client_company:
        from .services import sync_client_advances
        sync_client_advances(instance.invoice.client_company)

@receiver(post_delete, sender=Payment)
def handle_payment_delete(sender, instance, **kwargs):
    """Trigger advance synchronization on payment deletion."""
    try:
        if instance.invoice and instance.invoice.client_company:
            from .services import sync_client_advances
            sync_client_advances(instance.invoice.client_company)
        
        # Recalculate invoice totals (only if invoice still exists)
        if instance.invoice:
            instance.invoice.update_totals()
    except Invoice.DoesNotExist:
        # Invoice is being deleted along with payments, skip updates
        pass

@receiver(post_save, sender=ClientAdvance)
def handle_client_advance_save(sender, instance, **kwargs):
    """Trigger advance synchronization on advance creation/update."""
    from .services import sync_client_advances
    sync_client_advances(instance.client)

@receiver(post_delete, sender=ClientAdvance)
def handle_client_advance_delete(sender, instance, **kwargs):
    """Trigger advance synchronization on advance deletion."""
    from .services import sync_client_advances
    sync_client_advances(instance.client)

@receiver(post_save, sender=Invoice)
def handle_invoice_save(sender, instance, created, **kwargs):
    """Trigger advance synchronization on invoice creation or balance updates."""
    if instance.client_company:
        from .services import sync_client_advances
        
        # Recalculate remaining balances for all client advances
        sync_client_advances(instance.client_company)

@receiver(post_delete, sender=Invoice)
def handle_invoice_delete(sender, instance, **kwargs):
    """Recalibration not needed for other records upon invoice deletion."""
    pass

@receiver(post_delete, sender=InvoiceItem)
def handle_invoice_item_delete(sender, instance, **kwargs):
    """
    When an InvoiceItem is deleted (e.g. when its Invoice is deleted),
    check if the linked asset has any other active invoice items.
    If not, reset invoice_status back to NOT_INVOICED.
    """
    # Reset project_domain
    if instance.project_domain_id:
        has_other = InvoiceItem.objects.filter(
            project_domain_id=instance.project_domain_id
        ).exists()
        if not has_other:
            ProjectDomain.objects.filter(pk=instance.project_domain_id).update(
                invoice_status='NOT_INVOICED'
            )

    # Reset project_server
    if instance.project_server_id:
        has_other = InvoiceItem.objects.filter(
            project_server_id=instance.project_server_id
        ).exists()
        if not has_other:
            ProjectServer.objects.filter(pk=instance.project_server_id).update(
                invoice_status='NOT_INVOICED'
            )

    # Reset project_exbot
    if instance.project_exbot_id:
        has_other = InvoiceItem.objects.filter(
            project_exbot_id=instance.project_exbot_id
        ).exists()
        if not has_other:
            ProjectExbot.objects.filter(pk=instance.project_exbot_id).update(
                invoice_status='NOT_INVOICED'
            )

    # Reset project_service
    if instance.project_service_id:
        has_other = InvoiceItem.objects.filter(
            project_service_id=instance.project_service_id
        ).exists()
        if not has_other:
            ProjectService.objects.filter(pk=instance.project_service_id).update(
                invoice_status='NOT_INVOICED'
            )

    # Reset project_team
    if instance.project_team_id:
        has_other = InvoiceItem.objects.filter(
            project_team_id=instance.project_team_id
        ).exists()
        if not has_other:
            ProjectTeam.objects.filter(pk=instance.project_team_id).update(
                invoice_status='NOT_INVOICED'
            )

    # Reset project_finance
    if instance.project_finance_id:
        has_other = InvoiceItem.objects.filter(
            project_finance_id=instance.project_finance_id
        ).exists()
        if not has_other:
            ProjectFinance.objects.filter(pk=instance.project_finance_id).update(
                invoice_status='NOT_INVOICED'
            )

class ActivityExceedComment(models.Model):
    activity = models.ForeignKey(EmployeeDailyActivity,on_delete=models.CASCADE,related_name='exceed_comments',null=True,blank=True)
    project_service = models.ForeignKey('ProjectService',on_delete=models.CASCADE,related_name='exceed_comments',null=True,blank=True)
    commented_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='exceed_comments')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment on {self.activity} by {self.commented_by}"

class Notification(models.Model):   
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name='notifications',help_text="User who receives the notification")
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    activity = models.ForeignKey(EmployeeDailyActivity,on_delete=models.CASCADE,related_name='notifications',null=True,blank=True)
    comment = models.ForeignKey(ActivityExceedComment,on_delete=models.CASCADE,related_name='notifications',null=True,blank=True)
    notification_type = models.CharField(max_length=50, null=True, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ("view_server_notifications", "Can view server related notifications"),
            ("view_domain_notifications", "Can view domain related notifications"),
            ("view_exbot_notifications", "Can view exbot related notifications"),
        ]

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:50]}"

class EmployeeLeave(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leaves')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='leaves_approved')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20,blank=True,null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        permissions = [
            ("viewall_employeeleave", "Can view all employee leaves"),
            ("approve_employeeleave", "Can approve employee leave"),
            ("reject_employeeleave", "Can reject employee leave"),

        ]

    def __str__(self):
        return f"{self.employee.username}: {self.start_date} to {self.end_date} ({self.status})"

class Company(models.Model):
    company_profile = models.ManyToManyField('CompanyProfile', related_name='company') 
    employees = models.ManyToManyField(User, related_name='company') 
    projects = models.ManyToManyField("Project", related_name='company')
    invoices = models.ManyToManyField(Invoice, related_name='company')
    employee_leaves = models.ManyToManyField('EmployeeLeave', related_name='company')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)       

class CompanyProfile(models.Model):
    """Singleton model for company-wide settings (logo, name, type, contact)."""
    company_name = models.CharField(max_length=200, default="Extechnology")
    company_type = models.CharField(max_length=100, blank=True, default="", help_text="e.g. Software Company, IT Services")
    email        = models.EmailField(blank=True, default="")
    phone        = models.CharField(max_length=30, blank=True, default="")
    address      = models.CharField(max_length=300, blank=True, default="")
    logo         = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    
    bank_name = models.CharField(max_length=200, blank=True, default="Federal Bank")
    account_name = models.CharField(max_length=200, blank=True, default="Exmedia")
    account_number = models.CharField(max_length=100, blank=True, default="1234567890")
    ifsc_code = models.CharField(max_length=50, blank=True, default="FDRL0001234")
    upi_id = models.CharField(max_length=100, blank=True, default="exmedia@upi")

    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Company Settings"
        verbose_name_plural = "Company Settings"

    def __str__(self):
        return self.company_name

     

class Salary(models.Model):
    status_choices = (
        ('Paid', 'Paid'),
        ('Unpaid', 'Unpaid'),
        ('Partial', 'Partial'),
    )
    status = models.CharField(max_length=20, choices=status_choices, default='Unpaid')
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="salaries")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    basic = models.DecimalField(max_digits=10, decimal_places=2)
    working_days = models.IntegerField(default=26)
    present_days = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    overtime_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    late_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    advance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.username} ({self.start_date} to {self.end_date})"

class Attendance(models.Model):
    STATUS_CHOICES = (
        ('Present', 'Present'),
        ('Absent', 'Absent'),
        ('HalfDay', 'Half Day'),
        ('Leave', 'Leave'),
        ('WorkFromHome', 'Work From Home'),
    )

    APPROVAL_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    )

    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField()
    check_in = models.TimeField(blank=True, null=True)
    check_out = models.TimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    approval_status = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default='Pending')

    overtime_hours = models.FloatField(default=0)
    late_minutes = models.IntegerField(default=0)

    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-date']
        permissions = [
            ("approve_attendance", "Can approve attendance"),
            ("reject_attendance", "Can reject attendance"),
        ]

    def __str__(self):
        return f"{self.employee.username} - {self.date} - {self.status}"

class Employee(models.Model):
    photo = models.ImageField(upload_to='employee_photos/', null=True, blank=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    employee_id = models.CharField(max_length=20, unique=True)
    joining_date = models.DateField()
    department = models.CharField(max_length=100, blank=True, null=True)
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.employee_id}"   
   
class UserSalary(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_salary')
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    working_days = models.IntegerField(default=26)
    joining_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.base_salary} ({self.working_days} days)"

class OtherIncome(models.Model):

    title = models.CharField(max_length=200)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class OtherExpense(models.Model):

    title = models.CharField(max_length=200)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

def get_cycle_end_date(start_date, working_days=26):
    """
    Calculate end_date by counting forward `working_days` non-Sunday days.
    Sunday (weekday() == 6) is a weekly off and is NOT counted.
    Returns the last working day of the cycle.
    """
    count = 0
    current = start_date
    while count < working_days:
        if current.weekday() != 6:  # 6 = Sunday
            count += 1
        if count < working_days:
            current += timedelta(days=1)
    return current

def get_cycle_for_date(joining_date, target_date, working_days=26):
    """
    Finds the start_date and end_date of the 26-non-Sunday-day cycle
    that contains the given target_date.
    """
    current_start = joining_date
    while True:
        current_end = get_cycle_end_date(current_start, working_days)
        if current_start <= target_date <= current_end:
            return current_start, current_end
        if target_date < current_start:
            break
        # Move to next cycle start (day after end)
        current_start = current_end + timedelta(days=1)
    return None, None

def calculate_salary(salary):
    employee = salary.employee

    attendance = Attendance.objects.filter(
        employee=employee,
        date__range=[salary.start_date, salary.end_date]
    )

    present_days = Decimal('0.00')
    overtime_hours = 0
    late_minutes = 0

    # Auto-count Sundays in cycle as paid days
    current_day = salary.start_date
    while current_day <= salary.end_date:
        if current_day.weekday() == 6:  # Sunday
            present_days += Decimal('1.00')
        current_day += timedelta(days=1)

    for a in attendance:
        if a.status == "Present":
            present_days += Decimal('1.00')
        elif a.status == "HalfDay":
            present_days += Decimal('0.50')
        elif a.status == "WorkFromHome":
             present_days += Decimal('1.00')

        overtime_hours += a.overtime_hours
        late_minutes += a.late_minutes

    salary.present_days = present_days

    # Fetch UserSalary or Employee base salary and working days
    base_sal = Decimal('26000.00')
    w_days = 26

    user_sal_config = getattr(employee, 'user_salary', None)
    if user_sal_config:
        base_sal = user_sal_config.base_salary
        w_days = user_sal_config.working_days
    elif hasattr(employee, 'profile'):
        base_sal = employee.profile.basic_salary

    salary.basic = base_sal
    salary.working_days = w_days

    daily_salary = salary.basic / Decimal(str(salary.working_days)) if salary.working_days > 0 else Decimal('0.00')

    overtime_pay = Decimal(str(overtime_hours)) * Decimal('100.00')
    late_penalty = Decimal(str(late_minutes)) * Decimal('2.00')
    
    # Late penalty limit: penalty <= daily salary
    if late_penalty > daily_salary:
        late_penalty = daily_salary

    salary.overtime_pay = overtime_pay
    salary.late_deduction = late_penalty

    salary.total_salary = (
        (Decimal(str(present_days)) * daily_salary)
        + salary.overtime_pay
        + salary.bonus
        - salary.late_deduction
        - salary.advance
        - salary.deductions
    )

    salary.save()

@receiver(post_save, sender=Attendance)
def update_salary(sender, instance, **kwargs):
    employee = instance.employee
    
    joining_date = None
    # 1. Try to get joining_date from UserSalary (New preferred source)
    user_sal_config = getattr(employee, 'user_salary', None)
    if user_sal_config and user_sal_config.joining_date:
        joining_date = user_sal_config.joining_date
    
    # 2. Fallback to Employee profile
    if not joining_date and hasattr(employee, 'profile'):
        joining_date = employee.profile.joining_date

    if not joining_date:
        return

    today = instance.date
    # Calculate which cycle the attendance date falls in (skipping Sundays)
    w_days_temp = 26
    user_sal_config_temp = getattr(employee, 'user_salary', None)
    if user_sal_config_temp:
        w_days_temp = user_sal_config_temp.working_days
    
    start_date, end_date = get_cycle_for_date(joining_date, today, w_days_temp)
    if not start_date:
        return

    # Get basic salary and working days
    basic_sal = Decimal('26000.00')
    w_days = 26

    user_sal_config = getattr(employee, 'user_salary', None)
    if user_sal_config:
        basic_sal = user_sal_config.base_salary
        w_days = user_sal_config.working_days
    elif hasattr(employee, 'profile'):
        basic_sal = employee.profile.basic_salary

    salary, created = Salary.objects.get_or_create(
        employee=employee,
        start_date=start_date,
        end_date=end_date,
        defaults={
            "basic": basic_sal,
            "working_days": w_days
        }
    )

    calculate_salary(salary)

def generate_salary_records(employee, joining_date):
    """
    Auto-generates all 26-day salary cycles from joining_date to today.
    """
    today = timezone.now().date()
    current_start = joining_date
    
    # Get configuration
    basic_sal = Decimal('26000.00')
    w_days = 26
    user_sal_config = getattr(employee, 'user_salary', None)
    if user_sal_config:
        basic_sal = user_sal_config.base_salary
        w_days = user_sal_config.working_days
    elif hasattr(employee, 'profile'):
        basic_sal = employee.profile.basic_salary

    while current_start <= today:
        current_end = get_cycle_end_date(current_start, w_days)
        
        salary, created = Salary.objects.get_or_create(
            employee=employee,
            start_date=current_start,
            end_date=current_end,
            defaults={
                "basic": basic_sal,
                "working_days": w_days
            }
        )
        calculate_salary(salary)
        
        # Next cycle starts the day after the end
        current_start = current_end + timedelta(days=1)

@receiver(post_save, sender=UserSalary)
def auto_generate_cycles(sender, instance, **kwargs):
    if instance.joining_date:
        user = instance.user
        new_joining_date = instance.joining_date
        
        # Delete any salary records that start BEFORE the new joining date
        # (they belong to old cycle ranges that are now invalid)
        Salary.objects.filter(
            employee=user,
            start_date__lt=new_joining_date
        ).delete()
        
        # Regenerate all cycles from the new joining date
        generate_salary_records(user, new_joining_date)

@receiver(post_delete, sender=Attendance)
def delete_attendance_update_salary(sender, instance, **kwargs):
    employee = instance.employee
    # Find the salary record that covers this attendance date
    try:
        salary = Salary.objects.get(
            employee=employee,
            start_date__lte=instance.date,
            end_date__gte=instance.date
        )
        calculate_salary(salary)
    except Salary.DoesNotExist:
        pass

@receiver(post_delete, sender=InvoiceItem)
def reset_invoice_status_on_delete(sender, instance, **kwargs):
    if instance.project_domain:
        if not InvoiceItem.objects.filter(project_domain=instance.project_domain).exists():
            instance.project_domain.invoice_status = 'NOT_INVOICED'
            instance.project_domain.save(update_fields=['invoice_status'])
    
    if instance.project_server:
        if not InvoiceItem.objects.filter(project_server=instance.project_server).exists():
            instance.project_server.invoice_status = 'NOT_INVOICED'
            instance.project_server.save(update_fields=['invoice_status'])

    if instance.project_exbot:
        if not InvoiceItem.objects.filter(project_exbot=instance.project_exbot).exists():
            instance.project_exbot.invoice_status = 'NOT_INVOICED'
            instance.project_exbot.save(update_fields=['invoice_status'])

    if instance.project_service:
        if not InvoiceItem.objects.filter(project_service=instance.project_service).exists():
            instance.project_service.invoice_status = 'NOT_INVOICED'
            instance.project_service.save(update_fields=['invoice_status'])

    if instance.project_team:
        if not InvoiceItem.objects.filter(project_team=instance.project_team).exists():
            instance.project_team.invoice_status = 'NOT_INVOICED'
            instance.project_team.save(update_fields=['invoice_status'])

    if instance.project_finance:
        if not InvoiceItem.objects.filter(project_finance=instance.project_finance).exists():
            instance.project_finance.invoice_status = 'NOT_INVOICED'
            instance.project_finance.save(update_fields=['invoice_status'])

@receiver(models.signals.pre_save, sender=User)
def increment_token_version_on_role_change(sender, instance, **kwargs):
    if instance.id:
        try:
            old_instance = sender.objects.get(id=instance.id)
            if old_instance.role != instance.role:
                instance.token_version += 1
        except sender.DoesNotExist:
            pass

class Lead(models.Model):
    INTEREST_LEVEL = [
        ('hot', 'Hot'),
        ('warm', 'Warm'),
        ('cold', 'Cold'),
    ]

    CONVERSION_STATUS = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('proposal_sent', 'Proposal Sent'),
        ('negotiation', 'Negotiation'),
        ('approved', 'Approved'),
        ('closed', 'Closed'),
        ('denied', 'Denied'),
    ]

    FOLLOWUP_STATUS = [
        ('yes', 'Yes'),
        ('no', 'No'),
    ]

    company_name = models.CharField(max_length=255)
    nature_of_business = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.CharField(max_length=255, blank=True, null=True)

    contact_number = models.CharField(max_length=15)
    contact_person = models.CharField(max_length=255)

    contacted_date = models.DateField(null=True, blank=True)
    service_required = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True) # Keeping description as Strategic Notes for company details
    lead_source = models.CharField(max_length=100, blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_leads')
    assigned_role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_leads_role')
    attachment = models.FileField(upload_to='lead_files/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name

class FollowUp(models.Model):
    INTERACTION_TYPES = [
        ('call', 'Phone Call'),
        ('meeting', 'Direct Meeting'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
        ('rescheduled', 'Rescheduled'),
    ]

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='followups')
    interaction_date = models.DateField(default=timezone.now)
    note = models.TextField()
    followup_date = models.DateField(null=True, blank=True)
    interest_level = models.CharField(max_length=10, blank=True, null=True)
    conversion_status = models.CharField(max_length=20, blank=True, null=True)
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES, default='call')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_project_created = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Follow-up for {self.lead.company_name} on {self.followup_date}"

# Removed post_save signal because we will handle initial FollowUp creation in the Serializer.

class Schedule(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    schedule_date = models.DateField()
    schedule_time = models.TimeField()
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_schedules')
    assigned_role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='role_schedules')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_schedules')

    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.schedule_date} {self.schedule_time}"

class SystemAuditLog(models.Model):
    action = models.CharField(max_length=100)
    performed_by = models.CharField(max_length=255)
    target = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "System Audit Log"
        verbose_name_plural = "System Audit Logs"

    def __str__(self):
        return f"{self.action} on {self.target} by {self.performed_by}"
