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
    print(f"Access token: {access_token[:50]}...")
    
    # Create a test client
    client = Client(SERVER_NAME='127.0.0.1:8000')
    
    from django.test.utils import override_settings
    with override_settings(ALLOWED_HOSTS=['*']):
        # Test the list endpoint first
        print("\nTesting /api/attendance/ (list endpoint)")
        response = client.get(
            '/api/attendance/',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.get('Content-Type', 'Not set')}")
        if response.status_code != 200:
            print(f"Content: {response.content[:200]}")
        
        # Now test the export endpoint
        print("\nTesting /api/attendance/export/?format=excel&start_date=2026-06-02&end_date=2026-06-30")
        response = client.get(
            '/api/attendance/export/?format=excel&start_date=2026-06-02&end_date=2026-06-30',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.get('Content-Type', 'Not set')}")
        if response.status_code != 200:
            print(f"Content: {response.content[:200]}")
