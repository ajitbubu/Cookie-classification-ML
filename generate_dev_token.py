#!/usr/bin/env python3
"""
Generate a long-lived JWT token for development (bypassing login).
"""

import os
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Get JWT secret from environment
JWT_SECRET = os.getenv('JWT_SECRET_KEY', 'your-secret-key-here')

# Create token payload (valid for 1 year)
payload = {
    'sub': 'd6f7dd30-4947-4db2-bfd8-ead8771e7ed7',  # User ID
    'email': 'admin@example.com',
    'role': 'admin',
    'scopes': ['scans:read', 'scans:write', 'schedules:read', 'schedules:write', 'analytics:read'],
    'exp': datetime.utcnow() + timedelta(days=365),  # Valid for 1 year
    'iat': datetime.utcnow()
}

# Generate token
token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')

print("Generated JWT Token (valid for 1 year):")
print(token)
print("\nAdd this to your browser's localStorage as 'jwt_token'")
print("\nOr update dashboard/app/dashboard/layout.tsx with this token")
