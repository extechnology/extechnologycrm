import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import Project, ProjectServer, ProjectDomain, ProjectExbot, ProjectTeam, ProjectService, ProjectFinance

proj = Project.objects.first()
print("Project Name:", proj.name)
print("\n--- Teams ---")
for team in proj.project_teams.all():
    print(f"Team: {team.team.name if team.team else 'No Team'}, cost: {team.cost}, status: {team.status}, payment: {team.payment_status}")

print("\n--- Services ---")
for s in proj.services.all():
    print(f"Service: {s.name}, cost: {s.cost}, payment: {s.payment_status}")

print("\n--- Servers ---")
for s in proj.project_servers.all():
    print(f"Server: {s.name}, cost: {s.cost}, accrued_by: {s.accrued_by}, payment: {s.payment_status}")

print("\n--- Domains ---")
for d in proj.project_domains.all():
    print(f"Domain: {d.name}, cost: {d.cost}, accrued_by: {d.accrued_by}, payment: {d.payment_status}")

print("\n--- Exbots ---")
for ex in proj.project_exbots.all():
    print(f"Exbot: {ex.whatsapp_number}, cost: {ex.plan_rate}, payment: {ex.payment_status}")

print("\n--- Finances ---")
for pf in proj.project_finances.all():
    print(f"Finance: {pf.id}, cost: {pf.project_cost}, payment: {pf.payment_status}")
