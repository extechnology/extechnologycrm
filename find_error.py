import os
import django
import sys

# 1. Setup Django environment
# This allows the script to run outside of the web server
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.financial_views import BalanceSheetView
from djangosimplemissionapp.models import User
from django.test import RequestFactory
import traceback

def find_bug():
    """
    Simulates a PDF generation request and prints any errors to the console.
    """
    try:
        print("--- DEBUGGING BALANCE SHEET PDF ---")
        
        # Setup mock request
        from rest_framework.test import APIRequestFactory, force_authenticate
        factory = APIRequestFactory()
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.first()
            
        print(f"Using User: {user.username if user else 'None'}")
        
        # Mimic the browser request
        request = factory.get('/api/reports/balance-sheet/', {
            'filter_type': 'this_month', 
            'export': 'pdf'
        })
        
        # Execute view
        view = BalanceSheetView.as_view()
        force_authenticate(request, user=user)
        print("Generating PDF...")
        response = view(request)
        
        if response.status_code == 500:
            print("\n!!! ERROR: The view returned a 500 Status Code !!!")
            if hasattr(response, 'data'):
                print("Response Error Data:", response.data)
        else:
            print(f"\nSUCCESS! Status Code: {response.status_code}")
            print("PDF generation logic completed without crashing.")
            
    except Exception:
        print("\n!!! CRITICAL CRASH DETECTED !!!")
        traceback.print_exc()

if __name__ == "__main__":
    find_bug()
