#!/usr/bin/env python3
"""
Comprehensive diagnostic tool for scan deletion issues.
Checks API, database, and provides solutions.
"""

import asyncio
import asyncpg
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
# Use local API, not the legacy external API_URL
API_HOST = os.getenv('API_HOST', 'localhost')
API_PORT = os.getenv('API_PORT', '8000')
API_URL = f"http://{API_HOST}:{API_PORT}"

def print_header(title):
    """Print a formatted header."""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)
    print()

def print_section(title):
    """Print a section title."""
    print()
    print(f"--- {title} ---")
    print()

async def check_database():
    """Check database configuration."""
    print_header("DATABASE DIAGNOSTICS")
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set in .env file")
        return False
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Database connection successful")
        
        # Check tables
        print_section("1. Checking Tables")
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('scan_results', 'cookies')
        """)
        
        table_names = [t['table_name'] for t in tables]
        for table in ['scan_results', 'cookies']:
            if table in table_names:
                print(f"   ✅ {table} table exists")
            else:
                print(f"   ❌ {table} table NOT FOUND")
        
        # Check foreign key constraints
        print_section("2. Checking Foreign Key Constraints")
        constraints = await conn.fetch("""
            SELECT 
                tc.constraint_name,
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                rc.delete_rule
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            JOIN information_schema.referential_constraints AS rc
                ON rc.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name = 'cookies'
            AND ccu.table_name = 'scan_results'
        """)
        
        cascade_enabled = False
        if constraints:
            for c in constraints:
                print(f"   Constraint: {c['constraint_name']}")
                print(f"   Delete Rule: {c['delete_rule']}")
                
                if c['delete_rule'] == 'CASCADE':
                    print("   ✅ CASCADE DELETE is enabled")
                    cascade_enabled = True
                else:
                    print(f"   ⚠️  DELETE rule is {c['delete_rule']} (should be CASCADE)")
                    print()
                    print("   FIX: Run this migration:")
                    print("   psql $DATABASE_URL -f database/migrations/006_fix_schedule_cascade_delete.sql")
        else:
            print("   ⚠️  No foreign key constraints found")
        
        # Check scan count
        print_section("3. Checking Scan Data")
        scan_count = await conn.fetchval("SELECT COUNT(*) FROM scan_results")
        cookie_count = await conn.fetchval("SELECT COUNT(*) FROM cookies")
        
        print(f"   Total scans: {scan_count}")
        print(f"   Total cookies: {cookie_count}")
        
        if scan_count == 0:
            print()
            print("   ⚠️  No scans in database. Create a test scan first:")
            print("   python create_test_scan.py")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {type(e).__name__}: {e}")
        return False

def check_api():
    """Check API availability."""
    print_header("API DIAGNOSTICS")
    
    try:
        # Check health endpoint
        print_section("1. Checking API Health")
        response = requests.get(f"{API_URL}/health", timeout=5)
        
        if response.status_code == 200:
            print(f"   ✅ API is running at {API_URL}")
            print(f"   Response: {response.json()}")
        else:
            print(f"   ⚠️  API returned status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Cannot connect to API at {API_URL}")
        print()
        print("   The API is not running. Start it with:")
        print("   python run_api.py")
        print()
        print("   Or check if it's running on a different port.")
        return False
        
    except Exception as e:
        print(f"   ❌ API error: {type(e).__name__}: {e}")
        return False
    
    # Check delete endpoint
    print_section("2. Checking Delete Endpoint")
    print(f"   Delete by UUID: DELETE {API_URL}/api/v1/scans/{{scan_id}}")
    print(f"   Delete by domain: DELETE {API_URL}/api/v1/scans/by-domain?domain={{domain}}")
    print()
    print("   Both endpoints require authentication token.")
    
    return True

def show_solutions():
    """Show common solutions."""
    print_header("COMMON ISSUES & SOLUTIONS")
    
    print("Issue 1: 'Request validation failed'")
    print("   Cause: Sending domain name instead of UUID")
    print("   Solution: Use the /by-domain endpoint:")
    print("   DELETE /api/v1/scans/by-domain?domain=https://example.com")
    print()
    
    print("Issue 2: 'Foreign key constraint violation'")
    print("   Cause: CASCADE DELETE not configured")
    print("   Solution: Run migration:")
    print("   psql $DATABASE_URL -f database/migrations/006_fix_schedule_cascade_delete.sql")
    print()
    
    print("Issue 3: '404 Not Found'")
    print("   Cause: Scan doesn't exist")
    print("   Solution: Check scan exists in database:")
    print("   psql $DATABASE_URL -c 'SELECT scan_id, domain FROM scan_results LIMIT 5;'")
    print()
    
    print("Issue 4: 'API not responding'")
    print("   Cause: API server not running")
    print("   Solution: Start the API:")
    print("   python run_api.py")
    print()

def show_test_commands():
    """Show test commands."""
    print_header("TEST COMMANDS")
    
    print("1. Test deletion via database (interactive):")
    print("   python test_scan_delete_debug.py")
    print()
    
    print("2. Test deletion via API (requires token):")
    print("   # Get a token first")
    print("   python generate_dev_token.py")
    print()
    print("   # Then delete by UUID")
    print("   curl -X DELETE http://localhost:8000/api/v1/scans/{scan_id} \\")
    print("     -H 'Authorization: Bearer YOUR_TOKEN'")
    print()
    print("   # Or delete by domain")
    print("   curl -X DELETE 'http://localhost:8000/api/v1/scans/by-domain?domain=https://example.com' \\")
    print("     -H 'Authorization: Bearer YOUR_TOKEN'")
    print()
    
    print("3. Check what scans exist:")
    print("   psql $DATABASE_URL -c 'SELECT scan_id, domain, status FROM scan_results ORDER BY created_at DESC LIMIT 5;'")
    print()

async def main():
    """Run all diagnostics."""
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "SCAN DELETION DIAGNOSTIC TOOL" + " " * 23 + "║")
    print("╚" + "═" * 68 + "╝")
    
    # Check database
    db_ok = await check_database()
    
    # Check API
    api_ok = check_api()
    
    # Show solutions
    show_solutions()
    
    # Show test commands
    show_test_commands()
    
    # Summary
    print_header("SUMMARY")
    
    if db_ok and api_ok:
        print("✅ Database and API are both accessible")
        print()
        print("Next steps:")
        print("1. Run: python test_scan_delete_debug.py")
        print("2. This will test deletion and show any errors")
    elif db_ok:
        print("✅ Database is accessible")
        print("❌ API is not running")
        print()
        print("Start the API with: python run_api.py")
    else:
        print("❌ Cannot connect to database")
        print()
        print("Check your DATABASE_URL in .env file")
    
    print()

if __name__ == "__main__":
    asyncio.run(main())
