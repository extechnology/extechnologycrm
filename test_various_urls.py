#!/usr/bin/env python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangosimplemission.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

user = User.objects.filter(is_superuser=True).first()
client = Client(SERVER_NAME='127.0.0.1:8000')

from django.test.utils import override_settings
with override_settings(ALLOWED_HOSTS=['*']):
    # Test various URLs
    urls_to_test = [
        '/api/attendance/export/',
        '/api/attendance/export/?format=excel',
        '/api/attendance/export/?format=word',
        '/api/attendance/export/?start_date=2026-06-02',
        '/api/attendance/export/?end_date=2026-06-30',
        '/api/attendance/export/?xyz=abc',
    ]
    
    for url in urls_to_test:
        response = client.get(url)
        print(f"{url} -> {response.status_code}")
