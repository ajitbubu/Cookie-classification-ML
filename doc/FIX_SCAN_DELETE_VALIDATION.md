# Fix: "Request validation failed" When Deleting Scan

## Problem

When trying to delete a scan from the dashboard, you get: **"Request validation failed"**

## Root Cause

The API endpoint expects a **valid UUID** for `scan_id`, but the dashboard might be sending:
- ❌ Domain name (e.g., "ajittech.com")
- ❌ Invalid UUID format
- ❌ Wrong parameter name

## The API Expects

```
DELETE /api/v1/scans/{scan_id}
```

Where `scan_id` must be a **valid UUID v4** like:
```
550e8400-e29b-41d4-a716-446655440000
```

## Quick Fix

### Option 1: Get the Correct scan_id

The dashboard should use the `scan_id` from the scan results, not the domain name.

**Check what scan_ids exist:**

```bash
# List all scans and their IDs
psql -d your_database -c "
SELECT scan_id, domain, status, created_at
FROM scan_results
ORDER BY created_at DESC
LIMIT 10;
"
```

**Example output:**
```
               scan_id                | domain              | status  | created_at
--------------------------------------+---------------------+---------+-------------------
 a1b2c3d4-e5f6-4789-a012-b3c4d5e6f789 | https://ajittech.com| success | 2025-01-15 10:30:00
```

**Use this UUID in the delete request:**

```bash
# Correct ✅
curl -X DELETE http://localhost:8000/api/v1/scans/a1b2c3d4-e5f6-4789-a012-b3c4d5e6f789 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Option 2: Fix the Dashboard Code

If you control the dashboard code, ensure it's sending the `scan_id`, not the domain:

**Before (❌ Wrong):**
```javascript
// Sending domain instead of scan_id
fetch(`/api/v1/scans/${scan.domain}`, { method: 'DELETE' })
```

**After (✅ Correct):**
```javascript
// Send the scan_id
fetch(`/api/v1/scans/${scan.scan_id}`, { method: 'DELETE' })
```

## Validation Error Examples

### Example 1: Invalid UUID Format

**Request:**
```bash
DELETE /api/v1/scans/not-a-uuid
```

**Response:**
```json
{
  "detail": [
    {
      "loc": ["path", "scan_id"],
      "msg": "value is not a valid uuid",
      "type": "type_error.uuid"
    }
  ]
}
```

**Fix:** Use a valid UUID from the database

### Example 2: Using Domain Instead of UUID

**Request:**
```bash
DELETE /api/v1/scans/ajittech.com
```

**Response:**
```json
{
  "detail": [
    {
      "loc": ["path", "scan_id"],
      "msg": "value is not a valid uuid",
      "type": "type_error.uuid"
    }
  ]
}
```

**Fix:** Get the scan_id for that domain first:

```sql
SELECT scan_id FROM scan_results WHERE domain = 'https://ajittech.com';
```

Then use that UUID in the delete request.

## Testing

### 1. Get a Valid scan_id

```bash
# Option A: From database
psql -d your_database -c "
SELECT scan_id FROM scan_results LIMIT 1;
"

# Option B: From API
curl http://localhost:8000/api/v1/scans?page_size=1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. Test Delete with Valid UUID

```bash
# Use the scan_id from step 1
curl -X DELETE http://localhost:8000/api/v1/scans/YOUR-SCAN-ID-HERE \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -v

# Expected: 204 No Content (success)
```

### 3. Test Delete with Invalid Input

```bash
# This WILL fail with validation error (expected)
curl -X DELETE http://localhost:8000/api/v1/scans/invalid-uuid \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response: 422 Unprocessable Entity
```

## Debug: Check What the Dashboard is Sending

If you're using a browser dashboard, check the network tab:

1. Open browser DevTools (F12)
2. Go to Network tab
3. Try to delete a scan
4. Look at the DELETE request
5. Check the URL - it should be:
   ```
   DELETE /api/v1/scans/a1b2c3d4-e5f6-4789-a012-b3c4d5e6f789
   ```
   NOT:
   ```
   DELETE /api/v1/scans/ajittech.com  ❌
   ```

## Alternative: Delete by Domain (✅ NOW AVAILABLE!)

If the dashboard only has access to the domain name, you can use the new endpoint:

### New Endpoint: Delete by Domain (Already Implemented)

This endpoint has been added to `api/routers/scans.py`:

```python
@router.delete(
    "/by-domain",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete scan by domain",
    description="Delete the most recent scan for a domain"
)
async def delete_scan_by_domain(
    domain: str = Query(..., description="Domain name"),
    request: Request,
    current_user: TokenData = Depends(require_scope("scans:write"))
):
    """Delete the most recent scan for a domain."""
    db_pool = request.app.state.db_pool

    async with db_pool.acquire() as conn:
        # Get most recent scan for domain
        row = await conn.fetchrow(
            """
            SELECT scan_id FROM scan_results
            WHERE domain = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            domain
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"No scan found for domain {domain}"
            )

        scan_id = row['scan_id']

        # Delete cookies
        await conn.execute("DELETE FROM cookies WHERE scan_id = $1", scan_id)

        # Delete scan
        await conn.execute("DELETE FROM scan_results WHERE scan_id = $1", scan_id)

    return None
```

**Usage - This is Now Available!**

Option A: Using cURL
```bash
curl -X DELETE "http://localhost:8000/api/v1/scans/by-domain?domain=https://ajittech.com" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Option B: JavaScript (Dashboard)
```javascript
// Easy! Just use the domain name
const domain = encodeURIComponent('https://ajittech.com');
fetch(`/api/v1/scans/by-domain?domain=${domain}`, {
  method: 'DELETE',
  headers: {
    'Authorization': 'Bearer ' + token
  }
})
.then(response => {
  if (response.status === 204) {
    console.log('✅ Scan deleted successfully');
  }
})
.catch(error => console.error('❌ Delete failed:', error));
```

**This endpoint:**
- Finds the most recent scan for the domain
- Deletes it automatically
- No UUID lookup required!
- Returns 404 if no scan exists for that domain

## Summary

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Request validation failed" | Invalid UUID format | Use valid UUID from database |
| "value is not a valid uuid" | Sending domain instead of scan_id | Get scan_id first, then delete |
| 404 Not Found (after fixing UUID) | Scan doesn't exist | Check scan exists: `SELECT * FROM scan_results WHERE scan_id = '...'` |

## Common Mistakes

### ❌ Wrong: Using domain
```bash
DELETE /api/v1/scans/ajittech.com
```

### ❌ Wrong: Invalid UUID format
```bash
DELETE /api/v1/scans/123
```

### ✅ Correct: Valid UUID
```bash
DELETE /api/v1/scans/a1b2c3d4-e5f6-4789-a012-b3c4d5e6f789
```

## Get scan_id from Dashboard Data

If your dashboard is fetching scans from the API, the response includes `scan_id`:

```json
{
  "items": [
    {
      "scan_id": "a1b2c3d4-e5f6-4789-a012-b3c4d5e6f789",  ← Use this!
      "domain": "https://ajittech.com",
      "status": "success",
      ...
    }
  ]
}
```

Update your dashboard to use `scan.scan_id` for deletion, not `scan.domain`.

## Still Getting Validation Error?

Share these details for further help:

1. **The exact request being made:**
   ```bash
   # Copy from browser Network tab or curl command
   ```

2. **The full error response:**
   ```json
   {
     "detail": [ ... ]
   }
   ```

3. **Sample scan_id from database:**
   ```bash
   psql -d your_db -c "SELECT scan_id FROM scan_results LIMIT 1"
   ```
