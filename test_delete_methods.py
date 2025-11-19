#!/usr/bin/env python3
"""
Test script demonstrating both scan deletion methods
"""

import os
import sys
import asyncio
import asyncpg
from uuid import UUID


async def test_delete_methods():
    """Test both deletion methods - by UUID and by domain."""

    print("=" * 70)
    print("  Scan Deletion Methods Test")
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

        # List all scans
        print("1. Current scans in database:")
        scans = await conn.fetch("""
            SELECT scan_id, domain, status, created_at
            FROM scan_results
            ORDER BY created_at DESC
            LIMIT 10
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

        # Method 1: Delete by scan_id (UUID)
        print("=" * 70)
        print("  Method 1: Delete by scan_id (UUID)")
        print("=" * 70)
        print()
        print("This is the traditional method requiring the exact UUID.")
        print()

        if scans:
            test_scan = scans[0]
            scan_id = test_scan['scan_id']
            domain = test_scan['domain']

            print(f"Example scan:")
            print(f"  Domain: {domain}")
            print(f"  Scan ID: {scan_id}")
            print()
            print("API Request:")
            print(f"  DELETE /api/v1/scans/{scan_id}")
            print()
            print("cURL Command:")
            print(f"  curl -X DELETE http://localhost:8000/api/v1/scans/{scan_id} \\")
            print(f"    -H 'Authorization: Bearer YOUR_TOKEN'")
            print()
            print("JavaScript (Dashboard):")
            print(f"  fetch(`/api/v1/scans/${{scan.scan_id}}`, {{")
            print(f"    method: 'DELETE',")
            print(f"    headers: {{ 'Authorization': 'Bearer ' + token }}")
            print(f"  }})")
            print()

        # Method 2: Delete by domain (NEW)
        print("=" * 70)
        print("  Method 2: Delete by domain (NEW - Easier!)")
        print("=" * 70)
        print()
        print("This new method allows deletion using just the domain name.")
        print("It automatically finds and deletes the most recent scan for that domain.")
        print()

        if scans:
            test_scan = scans[0]
            domain = test_scan['domain']

            print(f"Example scan:")
            print(f"  Domain: {domain}")
            print()
            print("API Request:")
            print(f"  DELETE /api/v1/scans/by-domain?domain={domain}")
            print()
            print("cURL Command:")
            print(f"  curl -X DELETE 'http://localhost:8000/api/v1/scans/by-domain?domain={domain}' \\")
            print(f"    -H 'Authorization: Bearer YOUR_TOKEN'")
            print()
            print("JavaScript (Dashboard):")
            print(f"  const domain = encodeURIComponent('{domain}');")
            print(f"  fetch(`/api/v1/scans/by-domain?domain=${{domain}}`, {{")
            print(f"    method: 'DELETE',")
            print(f"    headers: {{ 'Authorization': 'Bearer ' + token }}")
            print(f"  }})")
            print()

        # Comparison
        print("=" * 70)
        print("  Comparison")
        print("=" * 70)
        print()

        print("Method 1: Delete by UUID")
        print("  ✅ Pros:")
        print("    - Precise control (delete specific scan)")
        print("    - Can delete older scans")
        print("  ❌ Cons:")
        print("    - Requires UUID lookup first")
        print("    - Dashboard must store/track UUIDs")
        print()

        print("Method 2: Delete by Domain (NEW)")
        print("  ✅ Pros:")
        print("    - No UUID lookup needed")
        print("    - Simple - just use domain name")
        print("    - Perfect for 'Delete Latest' button")
        print("  ❌ Cons:")
        print("    - Always deletes most recent scan")
        print("    - Can't choose which scan to delete")
        print()

        # Recommendation
        print("=" * 70)
        print("  Recommendation for Dashboard")
        print("=" * 70)
        print()
        print("Use Method 2 (by-domain) if:")
        print("  - You want to delete the latest scan for a domain")
        print("  - You only have domain name available")
        print("  - You want simpler code")
        print()
        print("Use Method 1 (by UUID) if:")
        print("  - You need to delete a specific older scan")
        print("  - You're showing a list of all scans with delete buttons")
        print("  - You already have the scan_id from API response")
        print()

        # Test both methods work (dry run)
        print("=" * 70)
        print("  Testing Both Methods (Dry Run)")
        print("=" * 70)
        print()

        if scans:
            # Test 1: Can we find scan by UUID?
            test_scan = scans[0]
            scan_id = test_scan['scan_id']

            row = await conn.fetchrow(
                "SELECT scan_id FROM scan_results WHERE scan_id = $1",
                scan_id
            )
            if row:
                print(f"✅ Method 1 would work: Found scan {scan_id}")
            else:
                print(f"❌ Method 1 would fail: Scan {scan_id} not found")

            # Test 2: Can we find scan by domain?
            domain = test_scan['domain']

            row = await conn.fetchrow(
                """
                SELECT scan_id FROM scan_results
                WHERE domain = $1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                domain
            )
            if row:
                print(f"✅ Method 2 would work: Found scan for {domain}")
            else:
                print(f"❌ Method 2 would fail: No scan found for {domain}")

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

    asyncio.run(test_delete_methods())
