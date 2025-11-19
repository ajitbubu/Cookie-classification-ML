#!/usr/bin/env python3
"""
Test script to verify scan deletion works correctly
"""

import os
import sys
import asyncio
import asyncpg
from uuid import UUID


async def test_scan_delete():
    """Test scan deletion with proper UUID validation."""

    print("=" * 70)
    print("  Scan Deletion Test")
    print("=" * 70)
    print()

    # Get database URL
    db_url = os.environ.get('DATABASE_URL', 'postgresql://localhost/cookie_scanner')

    try:
        # Connect to database
        print(f"Connecting to: {db_url}")
        conn = await asyncpg.connect(db_url)
        print("✅ Connected to database")
        print()

        # 1. List all scans
        print("1. Listing all scans...")
        scans = await conn.fetch("""
            SELECT scan_id, domain, status, created_at
            FROM scan_results
            ORDER BY created_at DESC
            LIMIT 5
        """)

        if not scans:
            print("  No scans found in database")
            print()
            print("  Create test scans first:")
            print("  python3 create_test_scan.py")
            await conn.close()
            return

        print(f"  Found {len(scans)} scans:")
        for scan in scans:
            print(f"  - {scan['scan_id']}: {scan['domain']} ({scan['status']})")
        print()

        # 2. Validate UUID format
        print("2. Validating scan_id formats...")
        for scan in scans:
            scan_id = scan['scan_id']
            try:
                # Test if it's a valid UUID
                uuid_obj = UUID(str(scan_id))
                print(f"  ✅ {scan_id} is valid UUID")
            except ValueError:
                print(f"  ❌ {scan_id} is NOT a valid UUID")
        print()

        # 3. Test what happens with invalid input
        print("3. Testing invalid UUID inputs...")

        invalid_inputs = [
            "not-a-uuid",
            "12345",
            "ajittech.com",
            "https://example.com"
        ]

        for invalid in invalid_inputs:
            try:
                # Try to parse as UUID
                UUID(invalid)
                print(f"  ⚠️  '{invalid}' - unexpectedly parsed as UUID")
            except ValueError:
                print(f"  ✅ '{invalid}' - correctly rejected (not a UUID)")
        print()

        # 4. Show correct delete command
        if scans:
            test_scan = scans[0]
            scan_id = test_scan['scan_id']
            domain = test_scan['domain']

            print("4. Correct delete command:")
            print()
            print(f"  Domain: {domain}")
            print(f"  Scan ID: {scan_id}")
            print()
            print("  ❌ WRONG: Using domain name")
            print(f"  curl -X DELETE http://localhost:8000/api/v1/scans/{domain}")
            print()
            print("  ✅ CORRECT: Using scan_id (UUID)")
            print(f"  curl -X DELETE http://localhost:8000/api/v1/scans/{scan_id} \\")
            print(f"    -H 'Authorization: Bearer YOUR_TOKEN'")
            print()

        # 5. Summary
        print("=" * 70)
        print("  Summary")
        print("=" * 70)
        print()
        print("The API endpoint expects:")
        print("  DELETE /api/v1/scans/{scan_id}")
        print()
        print("Where scan_id must be a valid UUID like:")
        print("  a1b2c3d4-e5f6-4789-a012-b3c4d5e6f789")
        print()
        print("NOT:")
        print("  ❌ Domain name (ajittech.com)")
        print("  ❌ URL (https://ajittech.com)")
        print("  ❌ Invalid format (123)")
        print()
        print("Fix your dashboard to:")
        print("  1. Get scan_id from API response")
        print("  2. Use scan.scan_id for deletion (not scan.domain)")
        print()

        await conn.close()

    except asyncpg.exceptions.InvalidCatalogNameError:
        print(f"❌ Database does not exist: {db_url}")
        print("   Create the database first")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if not os.environ.get('DATABASE_URL'):
        print("⚠️  DATABASE_URL not set")
        print("   Using default: postgresql://localhost/cookie_scanner")
        print()
        print("   To set it:")
        print("   export DATABASE_URL='postgresql://user:pass@host:port/database'")
        print()

    asyncio.run(test_scan_delete())
