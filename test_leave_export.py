#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import Token
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

User = get_user_model()

# Create a test client
client = Client()

# Get the superuser for testing
user = User.objects.filter(username='shamil123').first()
if not user:
    print("User shamil123 not found!")
    exit(1)

print(f"Testing with user: {user.username}")

# Generate a simple JWT token (basic version, skipping token_version check for testing)
from rest_framework_simplejwt.backends import TokenBackend

backend = TokenBackend(algorithm='HS256')

# Create a simple payload
import uuid
from datetime import datetime, timedelta

payload = {
    'token_type': 'access',
    'exp': datetime.utcnow() + timedelta(minutes=60),
    'iat': datetime.utcnow(),
    'jti': str(uuid.uuid4()),
    'user_id': user.id
}

# For testing, we'll use the API directly
print("\n" + "="*60)
print("Test 1: /api/employee-leaves/export/ (NO query params)")
print("="*60)
response = client.get(
    '/api/employee-leaves/export/',
)
print(f"Status: {response.status_code}")
print(f"Content: {response.content[:200]}")

print("\n" + "="*60)
print("Test 2: /api/employee-leaves/export/?export_format=excel")
print("="*60)
response = client.get(
    '/api/employee-leaves/export/?export_format=excel'
)
print(f"Status: {response.status_code}")
print(f"Content: {response.content[:200]}")

print("\n" + "="*60)
print("Test 3: With filters")
print("="*60)
response = client.get(
    '/api/employee-leaves/export/?export_format=excel&start_date=2026-01-01&end_date=2026-12-31',
)
print(f"Status: {response.status_code}")
print(f"Content: {response.content[:200]}")

print("\nTests completed!")
