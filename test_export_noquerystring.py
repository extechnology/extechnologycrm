#!/usr/bin/env python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangosimplemission.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

# Get the superuser
user = User.objects.filter(is_superuser=True).first()
if not user:
    print("No superuser found!")
else:
    print(f"Testing with user: {user.username}")
    
    # Get tokens for the user
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    
    # Create a test client
    client = Client(SERVER_NAME='127.0.0.1:8000')
    
    from django.test.utils import override_settings
    with override_settings(ALLOWED_HOSTS=['*']):
        # Test 1: WITHOUT query params
        print("\nTest 1: /api/attendance/export/ (NO query params)")
        response = client.get(
            '/api/attendance/export/',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        print(f"Status: {response.status_code}")
        print(f"Content: {response.content[:200]}")
        
        # Test 2: WITH export_format parameter (renamed from format)
        print("\nTest 2: /api/attendance/export/?export_format=excel&start_date=2026-06-02&end_date=2026-06-30")
        response = client.get(
            '/api/attendance/export/?export_format=excel&start_date=2026-06-02&end_date=2026-06-30',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        print(f"Status: {response.status_code}")
        print(f"Content: {response.content[:200]}")
        
        # Test 3: Using GET dict parameter with export_format
        print("\nTest 3: Using GET dict parameter with export_format")
        response = client.get(
            '/api/attendance/export/',
            {'export_format': 'excel', 'start_date': '2026-06-02', 'end_date': '2026-06-30'},
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        print(f"Status: {response.status_code}")
        print(f"Content: {response.content[:200]}")
