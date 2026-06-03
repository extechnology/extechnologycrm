import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import User, Role

print("--- USERS ---")
for u in User.objects.all():
    roles = u.role_names
    has_all_perf = u.has_perm('djangosimplemissionapp.view_all_employee_performance')
    has_all_act = u.has_perm('djangosimplemissionapp.view_all_activities')
    has_all_team = u.has_perm('djangosimplemissionapp.view_all_team_performance')
    has_viewall_user = u.has_perm('djangosimplemissionapp.viewall_user')
    print(f"User: {u.username} (ID: {u.id})")
    print(f"  Is Superuser: {u.is_superuser}, Is Staff: {u.is_staff}")
    print(f"  Role: {u.role.name if u.role else 'None'} -> role_names: {roles}")
    print(f"  has_perm('view_all_employee_performance'): {has_all_perf}")
    print(f"  has_perm('view_all_activities'): {has_all_act}")
    print(f"  has_perm('view_all_team_performance'): {has_all_team}")
    print(f"  has_perm('viewall_user'): {has_viewall_user}")
    print("-" * 30)
