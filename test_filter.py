#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import LoginUserDetails

# Test case-insensitive filter
print("Testing filters:\n")

# Filter 1: lowercase success
results = LoginUserDetails.objects.filter(login_status__iexact='success')
print(f"✅ login_status__iexact='success': {results.count()} records")

# Filter 2: uppercase SUCCESS
results = LoginUserDetails.objects.filter(login_status__iexact='SUCCESS')
print(f"✅ login_status__iexact='SUCCESS': {results.count()} records")

# Filter 3: mixed case
results = LoginUserDetails.objects.filter(login_status__iexact='SuCcEsS')
print(f"✅ login_status__iexact='SuCcEsS': {results.count()} records")

# Filter 4: device type
results = LoginUserDetails.objects.filter(device_type__iexact='desktop')
print(f"✅ device_type__iexact='desktop': {results.count()} records")

# Filter 5: combined filters
results = LoginUserDetails.objects.filter(login_status__iexact='success', device_type__iexact='desktop')
print(f"✅ Combined (success + desktop): {results.count()} records")

print("\nFirst record details:")
record = LoginUserDetails.objects.first()
if record:
    print(f"  User: {record.user.username}")
    print(f"  Status: {record.login_status}")
    print(f"  Device: {record.device_type}")
    print(f"  IP: {record.ip_address}")
    print(f"  Login Time: {record.login_time}")
    print(f"  Logout Time: {record.logout_time}")
    print(f"  Session Duration: {record.session_duration}")
