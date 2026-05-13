from reportlab.pdfgen import canvas
import sys
import os

def create_test():
    """
    Test script to verify if ReportLab can generate a PDF on the server.
    """
    filename = "server_test_output.pdf"
    try:
        print(f"--- PDF System Test ---")
        print(f"Python Version: {sys.version}")
        print(f"Working Directory: {os.getcwd()}")
        
        c = canvas.Canvas(filename)
        c.setFont("Helvetica", 12)
        c.drawString(100, 750, "Server PDF Generation Test")
        c.drawString(100, 730, f"Python Version: {sys.version[:50]}...")
        c.save()
        
        if os.path.exists(filename):
            print(f"\nSUCCESS! PDF was created as '{filename}'.")
            print(f"Size: {os.path.getsize(filename)} bytes")
        else:
            print(f"\nFAILED! File '{filename}' was not found after saving.")
            
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_test()
