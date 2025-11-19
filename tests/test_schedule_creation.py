#!/usr/bin/env python3
"""
Test schedule creation to debug the validation error.
"""

import requests
import json
from uuid import uuid4

# API endpoint
API_URL = "http://localhost:8000/api/v1"

# Get auth token (replace with your actual credentials)
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

# Test schedule creation
def test_create_schedule():
    token = get_token()
    if not token:
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test data matching what frontend sends
    schedule_data = {
        "domain_config_id": str(uuid4()),
        "domain": "https://ajittech.com",
        "scan_type": "quick",
        "scan_params": {},
        "frequency": "daily",
        "time_config": {
            "hour": 9,
            "minute": 0
        },
        "enabled": True
    }
    
    print("Sending schedule data:")
    print(json.dumps(schedule_data, indent=2))
    print()
    
    response = requests.post(
        f"{API_URL}/schedules",
        headers=headers,
        json=schedule_data
    )
    
    print(f"Response status: {response.status_code}")
    print("Response body:")
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    test_create_schedule()
