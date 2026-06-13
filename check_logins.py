#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import LoginUserDetails, User

# Check total records
total = LoginUserDetails.objects.count()
print(f"Total LoginUserDetails records: {total}")

# Check by status
success = LoginUserDetails.objects.filter(login_status='SUCCESS').count()
failed = LoginUserDetails.objects.filter(login_status='FAILED').count()
print(f"SUCCESS: {success}, FAILED: {failed}")

# Show first 5 records
print("\nLast 5 records:")
for record in LoginUserDetails.objects.order_by('-login_time')[:5]:
    print(f"  {record.user.username} - {record.login_status} - {record.login_time}")

# Check users
users = User.objects.count()
print(f"\nTotal users in database: {users}")
