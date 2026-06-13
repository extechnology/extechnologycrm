#!/usr/bin/env python
import os
import django
from unittest.mock import Mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangosimplemission.settings")
django.setup()

from django.test import RequestFactory
from djangosimplemissionapp.views import AttendanceExportAPIView
from djangosimplemissionapp.models import Attendance
from django.contrib.auth import get_user_model

User = get_user_model()

# Create a mock request
factory = RequestFactory()
user = User.objects.filter(is_superuser=True).first()

if not user:
    print("No superuser found!")
else:
    print(f"Testing with user: {user.username}")
    print(f"  - Superuser: {user.is_superuser}")
    print(f"  - Has viewall_attendance: {user.has_perm('djangosimplemissionapp.viewall_attendance')}")
    print(f"  - Has viewown_attendance: {user.has_perm('djangosimplemissionapp.viewown_attendance')}")
    
    # Create a GET request
    request = factory.get('/api/attendance/export/?format=excel&start_date=2026-06-02&end_date=2026-06-30')
    request.user = user
    
    # Manually test the permission logic from the view
    can_view_all = user.is_superuser or user.has_perm('djangosimplemissionapp.viewall_attendance')
    can_view_own = user.has_perm('djangosimplemissionapp.viewown_attendance') or can_view_all
    
    print(f"\nPermission logic:")
    print(f"  - can_view_all: {can_view_all}")
    print(f"  - can_view_own: {can_view_own}")
    print(f"  - Will pass permission check: {can_view_all or can_view_own}")
    
    # Check the queryset
    queryset = Attendance.objects.all().order_by('-date')
    print(f"\nQueryset:")
    print(f"  - Total records: {queryset.count()}")
    
    # Now try to call the view with debugging
    from rest_framework.response import Response
    from rest_framework.status import HTTP_404_NOT_FOUND
    
    # Patch the view to add debugging
    original_get = AttendanceExportAPIView.get
    
    def debug_get(self, request):
        print("\n>>> Entering view.get()")
        try:
            # Get format from request
            export_format = request.query_params.get('format', 'excel').lower()
            print(f"  - export_format: {export_format}")
            if export_format not in ['excel', 'word']:
                print(f"  - ERROR: Invalid format")
                return Response({'error': 'Invalid format. Use "excel" or "word"'}, status=400)

            # Get filtered queryset using same logic as list view
            user = request.user
            can_view_all = user.is_superuser or user.has_perm('djangosimplemissionapp.viewall_attendance')
            can_view_own = user.has_perm('djangosimplemissionapp.viewown_attendance') or can_view_all
            print(f"  - can_view_all: {can_view_all}")
            print(f"  - can_view_own: {can_view_own}")

            if not (can_view_all or can_view_own):
                print(f"  - ERROR: No permission")
                return Response({'error': 'You do not have permission to export attendance'}, status=403)

            queryset = Attendance.objects.all().order_by('-date')
            print(f"  - queryset.count(): {queryset.count()}")

            if not can_view_all:
                queryset = queryset.filter(employee=user)
            else:
                employee_id = request.query_params.get('employee')
                if employee_id:
                    queryset = queryset.filter(employee_id=employee_id)
            
            print(f"  - Filtered queryset.count(): {queryset.count()}")

            # Apply filters
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            print(f"  - start_date: {start_date}")
            print(f"  - end_date: {end_date}")
            
            if start_date:
                queryset = queryset.filter(date__gte=start_date)
            if end_date:
                queryset = queryset.filter(date__lte=end_date)
            
            print(f"  - Final queryset.count(): {queryset.count()}")

            if export_format == 'excel':
                print(f"  - Calling _export_to_excel()")
                return self._export_to_excel(queryset)
            else:
                print(f"  - Calling _export_to_word()")
                return self._export_to_word(queryset)
        except Exception as e:
            print(f"  - EXCEPTION: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    AttendanceExportAPIView.get = debug_get
    
    # Call the view
    view = AttendanceExportAPIView.as_view()
    try:
        response = view(request)
        print(f"\n=== Response status: {response.status_code} ===")
        if hasattr(response, 'data'):
            print(f"Response data: {response.data}")
    except Exception as e:
        print(f"\n=== Exception: {type(e).__name__}: {e} ===")
        import traceback
        traceback.print_exc()
