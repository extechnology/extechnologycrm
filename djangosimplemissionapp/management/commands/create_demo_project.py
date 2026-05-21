"""
Management Command: create_demo_project
---------------------------------------
Creates a single fully filled demo project with all related data:
  - Project + ProjectBaseInformation + ProjectExcution
  - ProjectClient (client info)
  - ProjectBusinessAddress (billing address)
  - ProjectDomain (2 domains)
  - ProjectServer (2 servers)
  - ProjectExbot (2 exbots / WhatsApp bots)
  - ProjectFinance (finance record)
  - Team + ProjectTeam (team allocation)
  - ProjectService + ProjectServiceTeam (service with team)
  - ProjectTeamMember (individual members)
  - ProjectDocument (2 document records)

Usage:
    python manage.py create_demo_project
    python manage.py create_demo_project --flush   (delete existing demo before re-creating)
"""

import sys
import io
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal


DEMO_PROJECT_NAME = "DEMO - ExTechnology CRM Platform"

OK  = "[OK]"
ERR = "[ERROR]"
WRN = "[WARN]"


class Command(BaseCommand):
    help = "Creates a fully filled demo project with all related data for testing."

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Delete the existing demo project before creating a new one.',
        )

    def _write(self, msg):
        """Safe stdout write that handles Windows cp1252 encoding."""
        try:
            self.stdout.write(msg)
        except UnicodeEncodeError:
            self.stdout.write(msg.encode('ascii', errors='replace').decode('ascii'))

    def handle(self, *args, **options):
        from djangosimplemissionapp.models import (
            Project, ProjectNature, ProjectBaseInformation, ProjectExcution,
            ProjectClient, ProjectBusinessAddress,
            ProjectDomain, ProjectServer, ProjectExbot,
            ProjectFinance, Team, ProjectTeam, ProjectTeamMember,
            ProjectService, ProjectServiceTeam, ProjectServiceMember,
            ProjectDocument, User, Role,
            DomainOrServerThirdPartyServiceProvider,
        )

        # --------------------------------------------------
        # 0. Optional flush
        # --------------------------------------------------
        if options['flush']:
            deleted_count, _ = Project.objects.filter(name=DEMO_PROJECT_NAME).delete()
            self._write(self.style.WARNING(
                f"{WRN} Flushed {deleted_count} existing demo project(s)."
            ))

        if Project.objects.filter(name=DEMO_PROJECT_NAME).exists():
            self._write(self.style.WARNING(
                f"{WRN} Demo project '{DEMO_PROJECT_NAME}' already exists. "
                "Run with --flush to recreate."
            ))
            return

        today = timezone.now().date()

        # --------------------------------------------------
        # 1. Get or create a superuser to act as team lead
        # --------------------------------------------------
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self._write(self.style.ERROR(
                f"{ERR} No superuser found. Please create a superuser first: "
                "python manage.py createsuperuser"
            ))
            return

        # Get a second user for member (could be the same if only one exists)
        member_user = User.objects.exclude(pk=admin_user.pk).first() or admin_user

        self._write(f"  Using admin user  : {admin_user.username}")
        self._write(f"  Using member user : {member_user.username}")

        # --------------------------------------------------
        # 2. Project Nature
        # --------------------------------------------------
        project_nature, _ = ProjectNature.objects.get_or_create(name="Software Development")
        self._write(f"  {OK} ProjectNature")

        # --------------------------------------------------
        # 3. Core Project
        # --------------------------------------------------
        project = Project.objects.create(
            name=DEMO_PROJECT_NAME,
            project_nature=project_nature,
            description=(
                "A fully featured demo project created by the create_demo_project command. "
                "It contains sample data across all modules: domain, server, exbot, "
                "finance, team, service, documents, and client info."
            ),
            status="Progressing",
            created_at=timezone.now() - timedelta(days=90),
        )
        self._write(f"  {OK} Project created (ID: {project.pk})")

        # --------------------------------------------------
        # 4. ProjectBaseInformation
        # --------------------------------------------------
        ProjectBaseInformation.objects.create(
            project=project,
            project_approach_date=today - timedelta(days=95),
            name=DEMO_PROJECT_NAME,
            description="Full-stack CRM platform with multi-tenant support, WhatsApp integration, and analytics dashboard.",
            creator_name="John Smith",
            creator_designation="Senior Project Manager",
        )
        self._write(f"  {OK} ProjectBaseInformation")

        # --------------------------------------------------
        # 5. ProjectExcution
        # --------------------------------------------------
        ProjectExcution.objects.create(
            project=project,
            work_assigned_date=today - timedelta(days=88),
            assigned_delivery_date=today + timedelta(days=60),
            start_date=today - timedelta(days=85),
            confirmed_end_date=today + timedelta(days=60),
            end_date=None,
        )
        self._write(f"  {OK} ProjectExcution")

        # --------------------------------------------------
        # 6. ProjectClient
        # --------------------------------------------------
        ProjectClient.objects.create(
            project=project,
            company_name="Acme Tech Solutions Pvt. Ltd.",
            contact_person="Ramesh Kumar",
            email="ramesh@acmetech.in",
            phone="9876543210",
        )
        self._write(f"  {OK} ProjectClient")

        # --------------------------------------------------
        # 7. ProjectBusinessAddress
        # --------------------------------------------------
        business_address = ProjectBusinessAddress.objects.create(
            gst_number="27AAPFU0939F1ZV",
            pan_number="AAPFU0939F",
            email="billing@acmetech.in",
            phone="04422334455",
            legal_name="Acme Tech Solutions Pvt. Ltd.",
            attention_name="Ramesh Kumar",
            unit_or_floor="3rd Floor",
            building_name="Tech Park Tower",
            plot_number="42",
            street_name="Anna Salai",
            landmark="Near Central Mall",
            locality="Teynampet",
            city="Chennai",
            district="Chennai",
            state="Tamil Nadu",
            pin_code="600018",
            country="India",
        )
        business_address.projects.add(project)
        self._write(f"  {OK} ProjectBusinessAddress")

        # --------------------------------------------------
        # 8. Third Party Provider
        # --------------------------------------------------
        provider, _ = DomainOrServerThirdPartyServiceProvider.objects.get_or_create(
            company_name="GoDaddy India",
            defaults={
                "contact_person": "Support Team",
                "email": "support@godaddy.com",
                "phone": "18001234567",
            }
        )
        self._write(f"  {OK} DomainOrServerThirdPartyServiceProvider")

        # --------------------------------------------------
        # 9. ProjectDomain (2 domains)
        # --------------------------------------------------
        domain1 = ProjectDomain.objects.create(
            project=project,
            client_address=business_address,
            name="acmetech.in",
            accrued_by="Extechnology",
            purchased_from="GoDaddy",
            purchase_date=today - timedelta(days=365),
            expiration_date=today + timedelta(days=270),   # active ~9 months left
            invoice_status="INVOICED",
            cost=Decimal("1200.00"),
            payment_status="PAID",
        )
        domain1.provider.add(provider)

        domain2 = ProjectDomain.objects.create(
            project=project,
            client_address=business_address,
            name="acmecrm.com",
            accrued_by="Client",
            purchased_from="Namecheap",
            purchase_date=today - timedelta(days=30),
            expiration_date=today + timedelta(days=20),    # expiring soon!
            invoice_status="NOT_INVOICED",
            cost=Decimal("800.00"),
            payment_status="UNPAID",
        )
        self._write(f"  {OK} ProjectDomain x2 (1 PAID active, 1 UNPAID expiring soon)")

        # --------------------------------------------------
        # 10. ProjectServer (2 servers)
        # --------------------------------------------------
        server1 = ProjectServer.objects.create(
            project=project,
            client_address=business_address,
            server_type="VPS",
            name="DigitalOcean",
            accrued_by="Extechnology",
            purchased_from="DigitalOcean",
            purchase_date=today - timedelta(days=180),
            expiration_date=today + timedelta(days=185),
            invoice_status="INVOICED",
            cost=Decimal("3600.00"),
            payment_status="PAID",
        )

        server2 = ProjectServer.objects.create(
            project=project,
            client_address=business_address,
            server_type="Shared",
            name="Hostinger",
            accrued_by="Client",
            purchased_from="Hostinger",
            purchase_date=today - timedelta(days=60),
            expiration_date=today + timedelta(days=25),    # expiring soon!
            invoice_status="NOT_INVOICED",
            cost=Decimal("1800.00"),
            payment_status="UNPAID",
        )
        self._write(f"  {OK} ProjectServer x2 (1 PAID VPS, 1 UNPAID Shared expiring soon)")

        # --------------------------------------------------
        # 11. ProjectExbot (2 WhatsApp bots)
        # --------------------------------------------------
        ProjectExbot.objects.create(
            project=project,
            whatsapp_number="+919876543210",
            plan_category="Business Pro",
            plan_active_date=today - timedelta(days=60),
            plan_deactive_date=today + timedelta(days=120),
            plan_rate=Decimal("2500.00"),
            payment_status="PAID",
            invoice_status="INVOICED",
            description="Primary WhatsApp business bot for customer support and lead generation.",
        )

        ProjectExbot.objects.create(
            project=project,
            whatsapp_number="+919123456789",
            plan_category="Starter",
            plan_active_date=today - timedelta(days=10),
            plan_deactive_date=today + timedelta(days=20),   # expiring soon!
            plan_rate=Decimal("1200.00"),
            payment_status="UNPAID",
            invoice_status="NOT_INVOICED",
            description="Secondary WhatsApp bot for marketing campaigns.",
        )
        self._write(f"  {OK} ProjectExbot x2 (1 PAID active, 1 UNPAID expiring soon)")

        # --------------------------------------------------
        # 12. ProjectFinance
        # --------------------------------------------------
        ProjectFinance.objects.create(
            project=project,
            project_cost=Decimal("150000.00"),
            manpower_cost=Decimal("80000.00"),
            total_invoiced=Decimal("90000.00"),
            total_paid=Decimal("60000.00"),
            total_balance_due=Decimal("30000.00"),
            invoice_status="INVOICED",
            payment_status="UNPAID",
        )
        self._write(f"  {OK} ProjectFinance")

        # --------------------------------------------------
        # 13. Team + ProjectTeam + ProjectTeamMember
        # --------------------------------------------------
        team, _ = Team.objects.get_or_create(
            name="Demo Dev Team",
            defaults={"team_lead": admin_user}
        )
        team.members.add(admin_user, member_user)

        project_team = ProjectTeam.objects.create(
            project=project,
            team=team,
            start_date=today - timedelta(days=80),
            deadline=today + timedelta(days=50),
            status="Progressing",
            invoice_status="INVOICED",
            payment_status="UNPAID",
            cost=Decimal("45000.00"),
            description="Core development team responsible for backend, frontend, and integration modules.",
        )

        # Team Members
        member1 = ProjectTeamMember.objects.create(
            project=project,
            employee=admin_user,
            role="Tech Lead / Backend Developer",
            cost=Decimal("25000.00"),
            allocated_days=60,
            actual_days_spent=45,
            start_date=today - timedelta(days=80),
            end_date=today + timedelta(days=50),
            status="Progressing",
            notes="Responsible for Django API, database architecture, and deployment pipeline.",
        )

        member2 = ProjectTeamMember.objects.create(
            project=project,
            employee=member_user,
            role="Frontend Developer",
            cost=Decimal("20000.00"),
            allocated_days=60,
            actual_days_spent=40,
            start_date=today - timedelta(days=80),
            end_date=today + timedelta(days=50),
            status="Progressing",
            notes="Responsible for React frontend, UI components, and API integration.",
        )

        # Link members to ProjectTeam
        project_team.members.add(member1, member2)
        self._write(f"  {OK} Team '{team.name}' + ProjectTeam + 2 ProjectTeamMembers")

        # --------------------------------------------------
        # 14. ProjectService + ProjectServiceTeam + ProjectServiceMember
        # --------------------------------------------------
        service1 = ProjectService.objects.create(
            project=project,
            client_address=business_address,
            name="WhatsApp Integration Module",
            description="Complete WhatsApp Cloud API integration including webhook setup, message handling, and multi-tenant credential management.",
            deadline=today + timedelta(days=30),
            status="Progressing",
            invoice_status="INVOICED",
            payment_status="PAID",
            cost=Decimal("18000.00"),
        )

        ProjectServiceTeam.objects.create(
            service=service1,
            team=team,
            start_date=today - timedelta(days=45),
            deadline=today + timedelta(days=30),
            status="Progressing",
        )

        ProjectServiceMember.objects.create(
            service=service1,
            employee=admin_user,
            role="Integration Developer",
            allocated_days=30,
            actual_days=22,
            cost=Decimal("12000.00"),
            start_date=today - timedelta(days=45),
            end_date=today + timedelta(days=30),
            status="Progressing",
            notes="Handling Meta API webhooks and credential flow.",
        )

        service2 = ProjectService.objects.create(
            project=project,
            client_address=business_address,
            name="Analytics Dashboard",
            description="Project and financial analytics dashboard with charts, filters, export to PDF, and date range controls.",
            deadline=today + timedelta(days=20),
            status="Completed",
            invoice_status="INVOICED",
            payment_status="PAID",
            cost=Decimal("12000.00"),
        )

        ProjectServiceTeam.objects.create(
            service=service2,
            team=team,
            start_date=today - timedelta(days=60),
            deadline=today - timedelta(days=5),
            actual_end_date=today - timedelta(days=7),
            status="Completed",
        )

        ProjectServiceMember.objects.create(
            service=service2,
            employee=member_user,
            role="Frontend Developer",
            allocated_days=25,
            actual_days=23,
            cost=Decimal("10000.00"),
            start_date=today - timedelta(days=60),
            end_date=today - timedelta(days=7),
            status="Completed",
            notes="Built React charts and filter components.",
        )
        self._write(f"  {OK} ProjectService x2 + ServiceTeams + ServiceMembers")

        # --------------------------------------------------
        # 15. ProjectDocument (2 documents)
        # --------------------------------------------------
        ProjectDocument.objects.create(
            project=project,
            name="Project Requirements Specification (PRS)",
            document=None,   # no actual file in demo
            description=(
                "Detailed requirements document covering all functional and non-functional "
                "requirements of the ExTechnology CRM Platform. Version 1.2."
            ),
        )

        ProjectDocument.objects.create(
            project=project,
            name="Technical Architecture Document",
            document=None,
            description=(
                "System architecture, database schema, API design patterns, "
                "and deployment architecture for the multi-tenant CRM."
            ),
        )
        self._write(f"  {OK} ProjectDocument x2")

        # --------------------------------------------------
        # Summary
        # --------------------------------------------------
        sep = "=" * 60
        self._write("")
        self._write(self.style.SUCCESS(sep))
        self._write(self.style.SUCCESS("  [DONE]  DEMO PROJECT CREATED SUCCESSFULLY!"))
        self._write(self.style.SUCCESS(sep))
        self._write(f"  Project ID   : {project.pk}")
        self._write(f"  Project Name : {project.name}")
        self._write(f"  Status       : {project.status}")
        self._write("")
        self._write("  Modules filled:")
        self._write("    [OK] ProjectBaseInformation")
        self._write("    [OK] ProjectExcution")
        self._write("    [OK] ProjectClient")
        self._write("    [OK] ProjectBusinessAddress")
        self._write("    [OK] ProjectDomain x2       (1 PAID, 1 UNPAID expiring soon)")
        self._write("    [OK] ProjectServer x2       (1 PAID, 1 UNPAID expiring soon)")
        self._write("    [OK] ProjectExbot x2        (1 PAID, 1 UNPAID expiring soon)")
        self._write("    [OK] ProjectFinance")
        self._write("    [OK] Team + ProjectTeam")
        self._write("    [OK] ProjectTeamMember x2")
        self._write("    [OK] ProjectService x2      (1 active, 1 completed)")
        self._write("    [OK] ProjectServiceTeam x2")
        self._write("    [OK] ProjectServiceMember x2")
        self._write("    [OK] ProjectDocument x2")
        self._write(self.style.SUCCESS(sep))
        self._write("")
        self._write("  To delete and recreate, run:")
        self._write("    python manage.py create_demo_project --flush")
        self._write("")
