#!/usr/bin/env python3
"""
Debug script to identify why schedule deletion is failing
"""

import asyncio
import asyncpg
import sys
import os


async def debug_delete_issue():
    """Debug schedule deletion issues."""

    print("=" * 70)
    print("  Schedule Deletion Debug Tool")
    print("=" * 70)
    print()

    # Get database URL from environment
    db_url = os.environ.get('DATABASE_URL', 'postgresql://localhost/cookie_scanner')

    print(f"Database: {db_url}")
    print()

    try:
        # Connect to database
        print("Connecting to database...")
        conn = await asyncpg.connect(db_url)
        print("✅ Connected")
        print()

        # 1. Check if schedules table exists
        print("1. Checking if schedules table exists...")
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'schedules'
            )
        """)
        if result:
            print("✅ schedules table exists")
        else:
            print("❌ schedules table not found - run migrations first!")
            return
        print()

        # 2. Check if schedule_executions table exists
        print("2. Checking if schedule_executions table exists...")
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'schedule_executions'
            )
        """)
        if result:
            print("✅ schedule_executions table exists")
        else:
            print("⚠️  schedule_executions table not found")
        print()

        # 3. Check foreign key constraint
        print("3. Checking foreign key constraint on schedule_executions...")
        constraints = await conn.fetch("""
            SELECT
                tc.constraint_name,
                kcu.column_name,
                rc.delete_rule
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            LEFT JOIN information_schema.referential_constraints rc
                ON tc.constraint_name = rc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'schedule_executions'
                AND kcu.column_name = 'schedule_id'
        """)

        if constraints:
            for constraint in constraints:
                print(f"  Constraint: {constraint['constraint_name']}")
                print(f"  Column: {constraint['column_name']}")
                print(f"  Delete Rule: {constraint['delete_rule']}")

                if constraint['delete_rule'] == 'CASCADE':
                    print("  ✅ CASCADE DELETE is enabled")
                else:
                    print(f"  ⚠️  DELETE rule is {constraint['delete_rule']} - should be CASCADE")
                    print("  👉 Run: psql -d your_db -f database/migrations/006_fix_schedule_cascade_delete.sql")
        else:
            print("  ⚠️  No foreign key constraint found")
        print()

        # 4. List all schedules
        print("4. Listing all schedules...")
        schedules = await conn.fetch("""
            SELECT schedule_id, domain, scan_type, frequency, enabled
            FROM schedules
            ORDER BY created_at DESC
            LIMIT 10
        """)

        if schedules:
            print(f"  Found {len(schedules)} schedules:")
            for schedule in schedules:
                print(f"  - {schedule['schedule_id']}: {schedule['domain']} ({schedule['scan_type']}, {schedule['frequency']})")
        else:
            print("  No schedules found")
        print()

        # 5. Check for executions blocking deletion
        print("5. Checking for schedule executions that might block deletion...")
        executions = await conn.fetch("""
            SELECT
                s.schedule_id,
                s.domain,
                COUNT(se.execution_id) as execution_count
            FROM schedules s
            LEFT JOIN schedule_executions se ON s.schedule_id = se.schedule_id
            GROUP BY s.schedule_id, s.domain
            HAVING COUNT(se.execution_id) > 0
            ORDER BY COUNT(se.execution_id) DESC
            LIMIT 10
        """)

        if executions:
            print(f"  Found {len(executions)} schedules with executions:")
            for exec_info in executions:
                print(f"  - {exec_info['schedule_id']}: {exec_info['domain']} has {exec_info['execution_count']} executions")
                print(f"    ⚠️  Deleting this schedule will fail unless CASCADE is enabled")
        else:
            print("  ✅ No schedules have executions")
        print()

        # 6. Test delete (dry run)
        if schedules:
            test_id = schedules[0]['schedule_id']
            print(f"6. Testing delete for schedule: {test_id}")
            print("   (Dry run - will rollback)")

            try:
                async with conn.transaction():
                    # Try to delete
                    result = await conn.fetchrow(
                        "DELETE FROM schedules WHERE schedule_id = $1 RETURNING schedule_id",
                        test_id
                    )

                    if result:
                        print(f"  ✅ Delete would succeed for {result['schedule_id']}")
                    else:
                        print(f"  ❌ Schedule {test_id} not found")

                    # Rollback
                    raise Exception("Rollback test")

            except Exception as e:
                if "Rollback test" in str(e):
                    print("  ✅ Test completed (transaction rolled back)")
                else:
                    print(f"  ❌ Delete failed: {e}")
                    print(f"  Error type: {type(e).__name__}")
        print()

        # Summary
        print("=" * 70)
        print("  SUMMARY")
        print("=" * 70)
        print()

        if constraints and constraints[0]['delete_rule'] == 'CASCADE':
            print("✅ Database is properly configured")
            print("   Schedule deletion should work")
        else:
            print("⚠️  Database needs migration")
            print("   Run this command:")
            print()
            print("   psql -d your_database -f database/migrations/006_fix_schedule_cascade_delete.sql")
        print()

        await conn.close()

    except asyncpg.exceptions.InvalidCatalogNameError:
        print(f"❌ Database does not exist: {db_url}")
        print("   Create the database first")
    except asyncpg.exceptions.InvalidPasswordError:
        print(f"❌ Authentication failed: {db_url}")
        print("   Check your database credentials")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print()
    print("This script will help identify why schedule deletion is failing")
    print()

    # Check if DATABASE_URL is set
    if not os.environ.get('DATABASE_URL'):
        print("⚠️  DATABASE_URL not set in environment")
        print("   Using default: postgresql://localhost/cookie_scanner")
        print()
        print("   To set it:")
        print("   export DATABASE_URL='postgresql://user:password@host:port/database'")
        print()

    asyncio.run(debug_delete_issue())
