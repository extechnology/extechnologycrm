#!/usr/bin/env python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangosimplemission.settings")
django.setup()

from django.urls import get_resolver

resolver = get_resolver()
print("Top-level URL patterns:")
for u in resolver.url_patterns:
    print(f"  {u.pattern}")

# Check included patterns
print("\nIncluded app URLs:")
from django.urls.resolvers import URLPattern, URLResolver
for u in resolver.url_patterns:
    if isinstance(u, URLResolver):
        print(f"\nPatterns under '{u.pattern}':")
        for sub_u in u.url_patterns:
            print(f"    {sub_u.pattern}")
            if 'attendance' in str(sub_u.pattern):
                print(f"      -> FOUND ATTENDANCE: {sub_u.pattern}")
