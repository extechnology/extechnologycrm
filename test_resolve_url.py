#!/usr/bin/env python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangosimplemission.settings")
django.setup()

from django.urls import resolve, Resolver404

# Try to resolve the URL
try:
    match = resolve('/api/attendance/export/')
    print(f"Resolved successfully!")
    print(f"  - View: {match.func}")
    print(f"  - View name: {match.view_name}")
    print(f"  - Args: {match.args}")
    print(f"  - Kwargs: {match.kwargs}")
except Resolver404 as e:
    print(f"Resolver404: {e}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
