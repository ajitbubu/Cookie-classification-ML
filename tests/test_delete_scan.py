#!/usr/bin/env python3
"""
Test scan deletion to verify the fix.
"""

import requests
import json

# API endpoint
API_URL = "http://localhost:8000/api/v1"

# Get auth token
def get_token():
    response = requests.post(
        f"{API_URL}/auth/login",
        json={
            "email": "admin@example.com",
            "password": "admin123"
        }
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Login failed: {response.status_code}")
        print(response.text)
        return None

# Test getting scans (to see the field mapping)
def test_get_scans():
    token = get_token()
    if not token:
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(
        f"{API_URL}/scans?page=1&page_size=5",
        headers=headers
    )
    
    print(f"Response status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"\nTotal scans: {data['total']}")
        print(f"\nFirst scan:")
        if data['items']:
            scan = data['items'][0]
            print(json.dumps(scan, indent=2))
            print(f"\nScan ID field: {scan.get('scan_id', 'NOT FOUND')}")
            return scan.get('scan_id')
    else:
        print("Response body:")
        print(json.dumps(response.json(), indent=2))
    
    return None

# Test deleting a scan
def test_delete_scan(scan_id):
    if not scan_id:
        print("No scan ID provided")
        return
    
    token = get_token()
    if not token:
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"\n\nAttempting to delete scan: {scan_id}")
    response = requests.delete(
        f"{API_URL}/scans/{scan_id}",
        headers=headers
    )
    
    print(f"Response status: {response.status_code}")
    if response.status_code == 204:
        print("✓ Scan deleted successfully!")
    else:
        print("Response body:")
        print(response.text)

if __name__ == "__main__":
    print("Testing scan retrieval...")
    scan_id = test_get_scans()
    
    if scan_id:
        # Ask for confirmation before deleting
        confirm = input(f"\nDelete scan {scan_id}? (y/n): ")
        if confirm.lower() == 'y':
            test_delete_scan(scan_id)
