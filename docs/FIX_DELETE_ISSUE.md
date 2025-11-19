# Fix: Schedule Deletion Failing

## Problem

When trying to delete a schedule, you're getting an error. This is likely caused by a **foreign key constraint** issue.

## Root Cause

The `schedule_executions` table has a foreign key reference to `schedules`. If a schedule has execution history, PostgreSQL prevents deletion to maintain data integrity **unless** CASCADE DELETE is configured.

## Quick Fix (2 steps)

### Step 1: Diagnose the Issue

Run the debug script to see exactly what's wrong:

```bash
# Set your database URL
export DATABASE_URL="postgresql://user:password@localhost:5432/your_database"

# Run diagnostic
python3 debug_delete_issue.py
```

**Expected output will show:**
```
⚠️  DELETE rule is NO ACTION - should be CASCADE
👉 Run: psql -d your_db -f database/migrations/006_fix_schedule_cascade_delete.sql
```

### Step 2: Apply the Fix

Run the migration to add CASCADE DELETE:

```bash
psql -d your_database -f database/migrations/006_fix_schedule_cascade_delete.sql
```

**What this does:**
- Updates the foreign key constraint on `schedule_executions`
- Enables CASCADE DELETE
- When you delete a schedule, all its executions are automatically deleted too

## Verification

After applying the fix, verify it worked:

```bash
# Run diagnostic again
python3 debug_delete_issue.py
```

Expected output:
```
✅ CASCADE DELETE is enabled
✅ Database is properly configured
   Schedule deletion should work
```

## Test Deletion

Now try deleting a schedule:

```bash
# Via API
curl -X DELETE http://localhost:8000/api/v1/schedules/{schedule_id} \
  -H "Authorization: Bearer YOUR_TOKEN"

# Should return: 204 No Content (success)
```

Or via database:

```sql
-- Should work now
DELETE FROM schedules WHERE schedule_id = 'your-schedule-id';
```

## Alternative: Manual Cleanup

If you can't run the migration, manually delete executions first:

```sql
-- 1. Find schedules with executions
SELECT s.schedule_id, s.domain, COUNT(se.execution_id) as exec_count
FROM schedules s
LEFT JOIN schedule_executions se ON s.schedule_id = se.schedule_id
GROUP BY s.schedule_id, s.domain
HAVING COUNT(se.execution_id) > 0;

-- 2. Delete executions for specific schedule
DELETE FROM schedule_executions WHERE schedule_id = 'your-schedule-id';

-- 3. Now delete the schedule
DELETE FROM schedules WHERE schedule_id = 'your-schedule-id';
```

## Understanding the Error

### Without CASCADE DELETE

```
ERROR: update or delete on table "schedules" violates foreign key constraint
       "schedule_executions_schedule_id_fkey" on table "schedule_executions"
DETAIL: Key (schedule_id)=(xxx) is still referenced from table "schedule_executions".
```

### With CASCADE DELETE (Fixed)

```
DELETE 1
-- Both schedule AND its executions are deleted automatically
```

## Database Schema

After the fix, the constraint looks like this:

```sql
ALTER TABLE schedule_executions
ADD CONSTRAINT schedule_executions_schedule_id_fkey
FOREIGN KEY (schedule_id)
REFERENCES schedules(schedule_id)
ON DELETE CASCADE;  -- ✅ This is the key part
```

## What Gets Deleted

When you delete a schedule, CASCADE automatically deletes:

| Table | What Gets Deleted |
|-------|-------------------|
| `schedules` | The schedule record |
| `schedule_executions` | All execution history for that schedule |

The scheduler will also:
- Detect the deletion (within 60 seconds)
- Remove the job from APScheduler
- Stop future executions

## Prevention

To avoid this issue in the future, always include CASCADE in foreign key constraints:

```sql
-- Good ✅
FOREIGN KEY (schedule_id) REFERENCES schedules(schedule_id) ON DELETE CASCADE

-- Bad ❌ (causes deletion failures)
FOREIGN KEY (schedule_id) REFERENCES schedules(schedule_id)
```

## Testing

After fixing, test with this sequence:

```bash
# 1. Create a test schedule
curl -X POST http://localhost:8000/api/v1/schedules \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "https://test.example.com",
    "domain_config_id": "550e8400-e29b-41d4-a716-446655440000",
    "scan_type": "quick",
    "frequency": "daily",
    "time_config": {"hour": 9, "minute": 0}
  }'

# 2. Note the returned schedule_id

# 3. Delete it
curl -X DELETE http://localhost:8000/api/v1/schedules/{schedule_id} \
  -H "Authorization: Bearer TOKEN"

# 4. Verify it's gone
curl http://localhost:8000/api/v1/schedules/{schedule_id} \
  -H "Authorization: Bearer TOKEN"

# Should return: 404 Not Found
```

## Summary

✅ **Problem**: Foreign key constraint prevents schedule deletion
✅ **Solution**: Apply migration 006 to add CASCADE DELETE
✅ **Result**: Schedules can be deleted along with their execution history

## Still Not Working?

If deletion still fails after applying the fix:

1. **Check the migration was applied:**
   ```sql
   SELECT delete_rule
   FROM information_schema.referential_constraints
   WHERE constraint_name = 'schedule_executions_schedule_id_fkey';
   -- Should return: CASCADE
   ```

2. **Check for other constraints:**
   ```sql
   SELECT constraint_name, constraint_type
   FROM information_schema.table_constraints
   WHERE table_name = 'schedules';
   ```

3. **Check API endpoint:**
   - Verify `/api/v1/schedules/{id}` endpoint is registered
   - Check authentication token is valid
   - Ensure user has `schedules:write` scope

4. **Run debug script:**
   ```bash
   python3 debug_delete_issue.py
   ```

Need more help? Include this information:
- Full error message
- Output from `debug_delete_issue.py`
- PostgreSQL version (`SELECT version();`)
