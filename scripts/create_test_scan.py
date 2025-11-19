#!/usr/bin/env python3
"""
Create test scan data for the dashboard.
"""

import os
import sys
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
import psycopg2
import json

# Load environment variables
load_dotenv()

def create_test_scans():
    """Create test scan data."""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("ERROR: DATABASE_URL not set in environment")
        sys.exit(1)
    
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Create test domain config ID
        domain_config_id = str(uuid.uuid4())
        
        # Create 5 test scans with different statuses
        test_scans = [
            {
                'domain': 'https://ajittech.com',
                'status': 'completed',
                'total_cookies': 15,
                'first_party': 8,
                'third_party': 7,
                'pages': 5,
                'duration': 45.2
            },
            {
                'domain': 'https://att.com',
                'status': 'completed',
                'total_cookies': 23,
                'first_party': 12,
                'third_party': 11,
                'pages': 8,
                'duration': 62.5
            },
            {
                'domain': 'https://xfinity.com',
                'status': 'completed',
                'total_cookies': 18,
                'first_party': 10,
                'third_party': 8,
                'pages': 6,
                'duration': 51.3
            },
            {
                'domain': 'https://stackoverflow.com',
                'status': 'running',
                'total_cookies': 0,
                'first_party': 0,
                'third_party': 0,
                'pages': 0,
                'duration': 0
            },
            {
                'domain': 'https://reddit.com',
                'status': 'failed',
                'total_cookies': 0,
                'first_party': 0,
                'third_party': 0,
                'pages': 0,
                'duration': 0
            }
        ]
        
        for i, scan in enumerate(test_scans):
            scan_id = str(uuid.uuid4())
            created_at = datetime.utcnow() - timedelta(hours=i)
            
            # Map status to match database constraints
            db_status = scan['status']
            if db_status == 'completed':
                db_status = 'success'
            
            cur.execute(
                """
                INSERT INTO scan_results (
                    scan_id, domain_config_id, domain, scan_mode, timestamp_utc,
                    status, error, total_cookies, duration_seconds, page_count,
                    created_at, updated_at, params
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    scan_id,
                    domain_config_id,
                    scan['domain'],
                    'quick',
                    created_at,
                    db_status,
                    'Connection timeout' if scan['status'] == 'failed' else None,
                    scan['total_cookies'],
                    scan['duration'],
                    scan['pages'],
                    created_at,
                    created_at,
                    json.dumps({})
                )
            )
            
            # Add some test cookies for completed scans
            if scan['status'] == 'completed':
                for j in range(min(5, scan['total_cookies'])):
                    cookie_id = str(uuid.uuid4())
                    cookie_type = 'First Party' if j < scan['first_party'] else 'Third Party'
                    cur.execute(
                        """
                        INSERT INTO cookies (
                            cookie_id, scan_id, name, domain, path,
                            http_only, secure, category, cookie_type, created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            cookie_id,
                            scan_id,
                            f'test_cookie_{j}',
                            scan['domain'].replace('https://', ''),
                            '/',
                            j % 2 == 0,
                            j % 2 == 1,
                            'necessary' if j < 2 else 'analytics',
                            cookie_type,
                            created_at
                        )
                    )
        
        conn.commit()
        
        print(f"✓ Created {len(test_scans)} test scans successfully!")
        print(f"\nYou can now view them in the dashboard at http://localhost:3000")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error creating test scans: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    create_test_scans()
