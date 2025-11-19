#!/usr/bin/env python3
"""
Test script to verify scan creation works properly
"""
import requests
import json

API_BASE = "http://localhost:8000/api/v1"

def login():
    """Login and get access token"""
    response = requests.post(
        f"{API_BASE}/auth/login",
        json={
            "email": "admin@example.com",
            "password": "admin123"
        }
    )
    response.raise_for_status()
    data = response.json()
    return data["access_token"]

def create_scan(token):
    """Create a new scan"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "domain": "https://example.com",
        "scan_mode": "quick",
        "params": {
            "max_pages": 5,
            "max_depth": 2
        }
    }
    
    response = requests.post(
        f"{API_BASE}/scans",
        headers=headers,
        json=payload
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response

if __name__ == "__main__":
    print("=== Testing Scan Creation ===\n")
    
    print("1. Logging in...")
    token = login()
    print(f"✓ Got token: {token[:50]}...\n")
    
    print("2. Creating scan...")
    response = create_scan(token)
    
    if response.status_code == 201:
        print("\n✓ Scan created successfully!")
    else:
        print(f"\n✗ Failed to create scan: {response.status_code}")
