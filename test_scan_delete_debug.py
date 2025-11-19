#!/usr/bin/env python3
"""
Debug script for scan deletion issues.
Tests both delete methods and shows detailed error information.
"""

import asyncio
import asyncpg
import os
from uuid import UUID
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

async def test_scan_deletion():
    """Test scan deletion and diagnose issues."""
    
    print("=" * 70)
    print("  SCAN DELETION DEBUG TOOL")
    print("=" * 70)
    print()
    
    if not DATABASE_URL:
        print("❌ ERROR: DATABASE_URL not set in .env file")
        return
    
    try:
        # Connect to database
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected to database")
        print()
        
        # 1. Check if scan_results table exists
        print("1. Checking database schema...")
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('scan_results', 'cookies')
        """)
        
        table_names = [t['table_name'] for t in tables]
        if 'scan_results' in table_names:
            print("   ✅ scan_results table exists")
        else:
            print("   ❌ scan_results table NOT FOUND")
            return
            
        if 'cookies' in table_names:
            print("   ✅ cookies table exists")
        else:
            print("   ❌ cookies table NOT FOUND")
        print()
        
        # 2. Check foreign key constraints
        print("2. Checking foreign key constraints...")
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
        
        if constraints:
            for c in constraints:
                print(f"   Constraint: {c['constraint_name']}")
                print(f"   Table: {c['table_name']}.{c['column_name']} -> {c['foreign_table_name']}.{c['foreign_column_name']}")
                print(f"   Delete Rule: {c['delete_rule']}")
                
                if c['delete_rule'] == 'CASCADE':
                    print("   ✅ CASCADE DELETE is enabled")
                else:
                    print(f"   ⚠️  DELETE rule is {c['delete_rule']} (should be CASCADE)")
        else:
            print("   ⚠️  No foreign key constraints found")
        print()
        
        # 3. List available scans
        print("3. Available scans in database:")
        scans = await conn.fetch("""
            SELECT 
                scan_id, 
                domain, 
                status, 
                created_at,
                (SELECT COUNT(*) FROM cookies WHERE cookies.scan_id = scan_results.scan_id) as cookie_count
            FROM scan_results
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        if not scans:
            print("   ⚠️  No scans found in database")
            print()
            print("   To test deletion, first create a scan:")
            print("   python create_test_scan.py")
            await conn.close()
            return
        
        print(f"   Found {len(scans)} scan(s):")
        print()
        for i, scan in enumerate(scans, 1):
            print(f"   {i}. Scan ID: {scan['scan_id']}")
            print(f"      Domain: {scan['domain']}")
            print(f"      Status: {scan['status']}")
            print(f"      Cookies: {scan['cookie_count']}")
            print(f"      Created: {scan['created_at']}")
            print()
        
        # 4. Test deletion
        print("4. Testing scan deletion...")
        print()
        
        # Ask user which scan to delete
        choice = input(f"Enter scan number to delete (1-{len(scans)}) or 'q' to quit: ").strip()
        
        if choice.lower() == 'q':
            print("Cancelled.")
            await conn.close()
            return
        
        try:
            scan_index = int(choice) - 1
            if scan_index < 0 or scan_index >= len(scans):
                print(f"❌ Invalid choice. Must be between 1 and {len(scans)}")
                await conn.close()
                return
        except ValueError:
            print("❌ Invalid input. Must be a number.")
            await conn.close()
            return
        
        selected_scan = scans[scan_index]
        scan_id = selected_scan['scan_id']
        domain = selected_scan['domain']
        cookie_count = selected_scan['cookie_count']
        
        print()
        print(f"Selected scan: {scan_id}")
        print(f"Domain: {domain}")
        print(f"Cookies to delete: {cookie_count}")
        print()
        
        confirm = input("Confirm deletion? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("Cancelled.")
            await conn.close()
            return
        
        print()
        print("Attempting deletion...")
        
        try:
            # Start transaction
            async with conn.transaction():
                # Method 1: Try direct deletion (will fail if no CASCADE)
                print("   Trying direct deletion of scan_results...")
                try:
                    result = await conn.execute(
                        "DELETE FROM scan_results WHERE scan_id = $1",
                        scan_id
                    )
                    print(f"   ✅ Direct deletion succeeded: {result}")
                    print()
                    print("✅ SCAN DELETED SUCCESSFULLY")
                    print()
                    print("   This means CASCADE DELETE is working properly.")
                    
                except asyncpg.exceptions.ForeignKeyViolationError as e:
                    print(f"   ❌ Direct deletion failed: {e}")
                    print()
                    print("   This means CASCADE DELETE is NOT configured.")
                    print("   Trying manual deletion of cookies first...")
                    
                    # Delete cookies first
                    cookie_result = await conn.execute(
                        "DELETE FROM cookies WHERE scan_id = $1",
                        scan_id
                    )
                    print(f"   ✅ Deleted cookies: {cookie_result}")
                    
                    # Now delete scan
                    scan_result = await conn.execute(
                        "DELETE FROM scan_results WHERE scan_id = $1",
                        scan_id
                    )
                    print(f"   ✅ Deleted scan: {scan_result}")
                    print()
                    print("✅ SCAN DELETED SUCCESSFULLY (with manual cookie deletion)")
                    print()
                    print("   ⚠️  RECOMMENDATION: Add CASCADE DELETE to foreign key")
                    print("   Run: psql -d your_db -f database/migrations/006_fix_schedule_cascade_delete.sql")
                    
        except Exception as e:
            print(f"   ❌ Deletion failed: {type(e).__name__}: {e}")
            print()
            print("   Full error details:")
            import traceback
            traceback.print_exc()
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_scan_deletion())
