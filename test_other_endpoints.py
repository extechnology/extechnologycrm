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
        # Test the salaries/summary endpoint (which is similar to export)
        print("\nTest 1: /api/salaries/summary/ (similar structure)")
        response = client.get(
            '/api/salaries/summary/',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        print(f"Status: {response.status_code}")
        
        # Test with query params
        print("\nTest 2: /api/salaries/summary/?start_date=2026-06-02")
        response = client.get(
            '/api/salaries/summary/?start_date=2026-06-02',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        print(f"Status: {response.status_code}")
