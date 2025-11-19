#!/usr/bin/env python3
"""
Create an admin user for the Cookie Scanner Platform.
"""

import os
import sys
import uuid
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

from src.api.auth.password import hash_password

def create_admin_user():
    """Create an admin user."""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("ERROR: DATABASE_URL not set in environment")
        sys.exit(1)
    
    # Default admin credentials
    email = "admin@example.com"
    password = "admin123"
    username = "admin"
    
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Check if user already exists
        cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        existing = cur.fetchone()
        
        if existing:
            print(f"User {email} already exists!")
            cur.close()
            conn.close()
            return
        
        # Hash password
        password_hash = hash_password(password)
        
        # Create user
        user_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO users (user_id, email, password_hash, role, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (user_id, email, password_hash, 'admin')
        )
        
        conn.commit()
        
        print(f"✓ Admin user created successfully!")
        print(f"  Email: {email}")
        print(f"  Password: {password}")
        print(f"  Username: {username}")
        print(f"\nYou can now log in to the dashboard at http://localhost:3000")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error creating admin user: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    create_admin_user()
