#!/usr/bin/env python
import os
import django
import json
from unittest.mock import Mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangosimplemission.settings")
django.setup()

from django.test import RequestFactory
from djangosimplemissionapp.views import AttendanceExportAPIView
from django.contrib.auth import get_user_model

User = get_user_model()

# Create a mock request
factory = RequestFactory()
user = User.objects.filter(is_superuser=True).first()

if not user:
    print("No superuser found!")
else:
    print(f"Testing with user: {user.username} (superuser: {user.is_superuser})")
    
    # Create a GET request
    request = factory.get('/api/attendance/export/?format=excel&start_date=2026-06-02&end_date=2026-06-30')
    request.user = user
    
    # Call the view
    view = AttendanceExportAPIView.as_view()
    try:
        response = view(request)
        print(f"Response status: {response.status_code}")
        if hasattr(response, 'data'):
            print(f"Response data: {response.data}")
        else:
            print(f"Response type: {type(response)}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
