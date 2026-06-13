#!/usr/bin/env python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangosimplemission.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
import json

User = get_user_model()

# Get the superuser
user = User.objects.filter(is_superuser=True).first()
if not user:
    print("No superuser found!")
else:
    print(f"Testing with user: {user.username}")
    print(f"User token_version: {user.token_version}")
    
    # Generate a proper token
    refresh = RefreshToken.for_user(user)
    access_token_obj = refresh.access_token
    
    # Check the token payload
    print(f"\nToken payload:")
    print(f"  - token_version: {access_token_obj.get('token_version')}")
    print(f"  - user_id: {access_token_obj.get('user_id')}")
    
    access_token = str(access_token_obj)
    
    # Create a test client
    client = Client(SERVER_NAME='127.0.0.1:8000')
    
    from django.test.utils import override_settings
    with override_settings(ALLOWED_HOSTS=['*']):
        # Test with proper token
        print("\nTest 1: /api/attendance/export/ (NO query params)")
        response = client.get(
            '/api/attendance/export/',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        print(f"Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Content: {response.content}")
        
        # Test with query params
        print("\nTest 2: /api/attendance/export/?format=excel")
        response = client.get(
            '/api/attendance/export/?format=excel',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        print(f"Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Content: {response.content}")
