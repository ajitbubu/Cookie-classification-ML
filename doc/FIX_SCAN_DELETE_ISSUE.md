# Fix: Scan Delete Not Working

## Diagnosis Complete ✅

I've run diagnostics on your system. Here's what I found:

### What's Working:
- ✅ Database is accessible
- ✅ CASCADE DELETE is properly configured
- ✅ You have 5 scans in the database
- ✅ Delete endpoints are implemented correctly

### The Problem:
- ❌ **API is not running**

## Solution

Your delete functionality will work once you start the API server.

### Start the API:

```bash
python run_api.py
```

Or if you prefer using uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Testing Delete After Starting API

### Method 1: Delete by Domain (Easiest)

```bash
# Get an auth token first
python generate_dev_token.py

# Delete the most recent scan for a domain
curl -X DELETE 'http://localhost:8000/api/v1/scans/by-domain?domain=https://example.com' \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

### Method 2: Delete by UUID

```bash
# First, get a scan_id
psql $DATABASE_URL -c "SELECT scan_id, domain FROM scan_results LIMIT 1;"

# Then delete it
curl -X DELETE http://localhost:8000/api/v1/scans/{scan_id} \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

### Method 3: Test via Database (No API needed)

If you want to test deletion without the API:

```bash
python test_scan_delete_debug.py
```

This will:
- Show all available scans
- Let you choose which one to delete
- Test the deletion directly in the database
- Show any errors

## Common Error Messages & Fixes

### Error: "Request validation failed"
**Cause**: Sending domain name instead of UUID to the UUID endpoint

**Fix**: Use the `/by-domain` endpoint instead:
```bash
DELETE /api/v1/scans/by-domain?domain=https://example.com
```

### Error: "Cannot connect to API"
**Cause**: API server not running

**Fix**: Start the API with `python run_api.py`

### Error: "404 Not Found"
**Cause**: Scan doesn't exist

**Fix**: Check what scans exist:
```bash
psql $DATABASE_URL -c "SELECT scan_id, domain FROM scan_results;"
```

### Error: "Foreign key constraint violation"
**Cause**: CASCADE DELETE not configured (but this is already fixed in your database!)

**Status**: ✅ Already working in your database

## API Endpoints Available

Once the API is running, you have two delete endpoints:

### 1. Delete by UUID
```
DELETE /api/v1/scans/{scan_id}
```
- Requires valid UUID
- Deletes specific scan
- Returns 204 No Content on success

### 2. Delete by Domain (NEW)
```
DELETE /api/v1/scans/by-domain?domain={domain}
```
- Accepts domain name
- Deletes most recent scan for that domain
- Returns 204 No Content on success
- Returns 404 if no scan found for domain

## Quick Test Sequence

```bash
# 1. Start the API
python run_api.py

# 2. In another terminal, generate a token
python generate_dev_token.py

# 3. List scans
curl http://localhost:8000/api/v1/scans \
  -H 'Authorization: Bearer YOUR_TOKEN'

# 4. Delete a scan by domain
curl -X DELETE 'http://localhost:8000/api/v1/scans/by-domain?domain=https://example.com' \
  -H 'Authorization: Bearer YOUR_TOKEN'

# 5. Verify it's deleted
curl http://localhost:8000/api/v1/scans \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

## Dashboard Integration

If you're using a dashboard, update your delete function:

```javascript
async function deleteScan(domain) {
  const encodedDomain = encodeURIComponent(domain);
  
  const response = await fetch(
    `/api/v1/scans/by-domain?domain=${encodedDomain}`,
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  if (response.status === 204) {
    console.log('✅ Scan deleted');
    // Refresh your scan list
  } else if (response.status === 404) {
    console.log('⚠️ No scan found for this domain');
  } else {
    console.error('❌ Delete failed');
  }
}
```

## Diagnostic Tools

I've created two diagnostic scripts for you:

### 1. Full Diagnostics
```bash
python diagnose_delete_issue.py
```
Shows:
- Database status
- API status
- Foreign key configuration
- Available scans
- Common solutions

### 2. Interactive Delete Test
```bash
python test_scan_delete_debug.py
```
Shows:
- All scans in database
- Lets you choose one to delete
- Tests deletion
- Shows detailed error messages

## Summary

**Your delete functionality is properly configured!** 

The only issue is that the API server needs to be running. Start it with:

```bash
python run_api.py
```

Then test deletion with:

```bash
python test_scan_delete_debug.py
```

Or via API:

```bash
curl -X DELETE 'http://localhost:8000/api/v1/scans/by-domain?domain=YOUR_DOMAIN' \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

## Need More Help?

Run the diagnostic tool to see current status:

```bash
python diagnose_delete_issue.py
```

This will show you exactly what's working and what needs attention.
