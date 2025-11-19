#!/usr/bin/env python3
"""
Simple script to test scan deletion via API.
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Use local API, not the legacy external API_URL
API_HOST = os.getenv('API_HOST', 'localhost')
API_PORT = os.getenv('API_PORT', '8000')
API_URL = f"http://{API_HOST}:{API_PORT}"

def test_delete():
    """Test scan deletion via API."""
    
    print("=" * 70)
    print("  SCAN DELETE API TEST")
    print("=" * 70)
    print()
    
    # Check if API is running
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        print(f"✅ API is running at {API_URL}")
        print()
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to API at {API_URL}")
        print()
        print("Start the API first:")
        print("  python run_api.py")
        print()
        return
    
    # Get token
    print("You need an authentication token to delete scans.")
    print()
    print("Generate one with:")
    print("  python generate_dev_token.py")
    print()
    
    token = input("Enter your auth token (or press Enter to skip): ").strip()
    
    if not token:
        print()
        print("Skipping API test. Run this script again with a token.")
        return
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    # List scans
    print()
    print("Fetching available scans...")
    try:
        response = requests.get(f"{API_URL}/api/v1/scans", headers=headers)
        
        if response.status_code == 401:
            print("❌ Invalid token. Generate a new one:")
            print("  python generate_dev_token.py")
            return
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch scans: {response.status_code}")
            print(response.text)
            return
        
        data = response.json()
        scans = data.get('items', [])
        
        if not scans:
            print("⚠️  No scans found. Create one first:")
            print("  python create_test_scan.py")
            return
        
        print(f"✅ Found {len(scans)} scan(s)")
        print()
        
        for i, scan in enumerate(scans, 1):
            print(f"{i}. Domain: {scan['domain']}")
            print(f"   Scan ID: {scan['scan_id']}")
            print(f"   Status: {scan['status']}")
            print(f"   Cookies: {scan.get('total_cookies', 0)}")
            print()
        
        # Choose scan to delete
        choice = input(f"Enter scan number to delete (1-{len(scans)}) or 'q' to quit: ").strip()
        
        if choice.lower() == 'q':
            print("Cancelled.")
            return
        
        try:
            scan_index = int(choice) - 1
            if scan_index < 0 or scan_index >= len(scans):
                print(f"❌ Invalid choice")
                return
        except ValueError:
            print("❌ Invalid input")
            return
        
        selected_scan = scans[scan_index]
        scan_id = selected_scan['scan_id']
        domain = selected_scan['domain']
        
        print()
        print(f"Selected: {domain}")
        print(f"Scan ID: {scan_id}")
        print()
        
        # Choose delete method
        print("Choose delete method:")
        print("1. Delete by UUID (precise)")
        print("2. Delete by domain (deletes most recent)")
        print()
        
        method = input("Enter method (1 or 2): ").strip()
        
        if method == '1':
            # Delete by UUID
            print()
            print(f"Deleting scan {scan_id}...")
            response = requests.delete(
                f"{API_URL}/api/v1/scans/{scan_id}",
                headers=headers
            )
            
            if response.status_code == 204:
                print("✅ Scan deleted successfully!")
            elif response.status_code == 404:
                print("❌ Scan not found")
            else:
                print(f"❌ Delete failed: {response.status_code}")
                print(response.text)
        
        elif method == '2':
            # Delete by domain
            print()
            print(f"Deleting most recent scan for {domain}...")
            response = requests.delete(
                f"{API_URL}/api/v1/scans/by-domain",
                params={'domain': domain},
                headers=headers
            )
            
            if response.status_code == 204:
                print("✅ Scan deleted successfully!")
            elif response.status_code == 404:
                print(f"❌ No scan found for domain {domain}")
            else:
                print(f"❌ Delete failed: {response.status_code}")
                print(response.text)
        
        else:
            print("❌ Invalid method")
            return
        
        # Verify deletion
        print()
        print("Verifying deletion...")
        response = requests.get(f"{API_URL}/api/v1/scans/{scan_id}", headers=headers)
        
        if response.status_code == 404:
            print("✅ Verified: Scan no longer exists")
        else:
            print("⚠️  Scan still exists (might be a different scan)")
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_delete()
