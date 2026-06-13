import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from django.utils import timezone
from djangosimplemissionapp.models import Attendance, User

user = User.objects.first()
if user:
    att = Attendance(employee=user, date='2026-06-11', status='Present')
    att.save()
    print(f'Created attendance with check_in: {att.check_in}')
    print(f'Server time (should be ~16:00): {timezone.now()}')
else:
    print("No user found")
