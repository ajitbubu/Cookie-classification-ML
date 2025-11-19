# Solution: Scan Deletion "Request Validation Failed" Error

## Problem Solved

Your dashboard was getting **"Request validation failed"** when trying to delete scans because it was sending the domain name instead of the required UUID.

## Solution Implemented

I've added a **new endpoint** that makes deletion easier - you can now delete scans using just the domain name!

---

## Two Ways to Delete Scans

### Method 1: Delete by UUID (Original)

**Endpoint:**
```
DELETE /api/v1/scans/{scan_id}
```

**When to use:**
- You have the scan_id available
- You want to delete a specific scan
- You're displaying a list of all scans

**Example:**
```javascript
// Dashboard code
fetch(`/api/v1/scans/${scan.scan_id}`, {
  method: 'DELETE',
  headers: { 'Authorization': 'Bearer ' + token }
})
```

**Note:** scan_id must be a valid UUID like `a1b2c3d4-e5f6-4789-a012-b3c4d5e6f789`

---

### Method 2: Delete by Domain (NEW - Recommended for Dashboard)

**Endpoint:**
```
DELETE /api/v1/scans/by-domain?domain={domain_name}
```

**When to use:**
- You only have the domain name
- You want to delete the latest scan for a domain
- You want simpler code

**Example:**
```javascript
// Dashboard code - Much simpler!
const domain = encodeURIComponent('https://ajittech.com');
fetch(`/api/v1/scans/by-domain?domain=${domain}`, {
  method: 'DELETE',
  headers: { 'Authorization': 'Bearer ' + token }
})
.then(response => {
  if (response.status === 204) {
    alert('Scan deleted successfully');
    refreshScanList();
  }
})
.catch(error => {
  console.error('Delete failed:', error);
});
```

**Benefits:**
✅ No UUID lookup needed
✅ Simpler code
✅ Works directly with domain names
✅ Perfect for "Delete Latest Scan" button

---

## Quick Fix for Your Dashboard

**Option A: Use the new by-domain endpoint (Easiest)**

Replace your delete code with:

```javascript
function deleteScan(domain) {
  const encodedDomain = encodeURIComponent(domain);

  fetch(`/api/v1/scans/by-domain?domain=${encodedDomain}`, {
    method: 'DELETE',
    headers: {
      'Authorization': 'Bearer ' + localStorage.getItem('token')
    }
  })
  .then(response => {
    if (response.status === 204) {
      console.log('✅ Deleted scan for', domain);
      // Refresh your scan list here
    } else if (response.status === 404) {
      alert('No scan found for this domain');
    } else {
      alert('Delete failed');
    }
  })
  .catch(error => {
    console.error('Error:', error);
    alert('Network error');
  });
}
```

**Option B: Use scan_id from API response**

When you fetch scans, the API returns scan_id:

```javascript
// When fetching scans
fetch('/api/v1/scans')
  .then(r => r.json())
  .then(data => {
    data.items.forEach(scan => {
      console.log('Scan ID:', scan.scan_id);     // ← Use this!
      console.log('Domain:', scan.domain);

      // Store scan_id and use it for deletion
      deleteScan(scan.scan_id);  // Not scan.domain!
    });
  });

function deleteScan(scanId) {
  fetch(`/api/v1/scans/${scanId}`, {  // Use UUID here
    method: 'DELETE',
    headers: { 'Authorization': 'Bearer ' + token }
  });
}
```

---

## Testing

Run this test script to see both methods in action:

```bash
python3 test_delete_methods.py
```

This will show you:
- How to use both deletion methods
- When to use each method
- Example API calls
- Example JavaScript code

---

## API Responses

### Success (204 No Content)
```
HTTP/1.1 204 No Content
```
Body is empty - deletion succeeded.

### Not Found (404)
```json
{
  "detail": "No scan found for domain: https://example.com"
}
```

### Validation Error (422) - Only with UUID method
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

---

## Which Method Should You Use?

### Use **Method 2 (by-domain)** if:
- ✅ Your dashboard shows domain names only
- ✅ You want to delete the latest scan
- ✅ You want simpler code
- ✅ You don't need to track scan_ids

### Use **Method 1 (by UUID)** if:
- ✅ You're showing a detailed list of all scans
- ✅ Users need to delete specific older scans
- ✅ You already have scan_id from previous API calls

---

## Common Mistakes Fixed

### ❌ Before (Wrong)
```javascript
// This causes "Request validation failed"
fetch(`/api/v1/scans/ajittech.com`, { method: 'DELETE' })
```

**Error:** "ajittech.com" is not a valid UUID

### ✅ After (Correct - Option 1)
```javascript
// Use the new by-domain endpoint
fetch(`/api/v1/scans/by-domain?domain=ajittech.com`, { method: 'DELETE' })
```

### ✅ After (Correct - Option 2)
```javascript
// Or use the scan_id from API response
fetch(`/api/v1/scans/a1b2c3d4-e5f6-4789-a012-b3c4d5e6f789`, { method: 'DELETE' })
```

---

## Implementation Checklist

- [x] New endpoint added to `api/routers/scans.py`
- [x] Endpoint supports deletion by domain name
- [x] Test script created (`test_delete_methods.py`)
- [x] Documentation updated
- [ ] Update your dashboard to use new endpoint
- [ ] Test with your dashboard
- [ ] Remove old broken delete code

---

## Still Having Issues?

1. **Run the test script:**
   ```bash
   python3 test_delete_methods.py
   ```

2. **Check the API is running:**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

3. **Verify authentication:**
   ```bash
   # Check your token is valid
   curl http://localhost:8000/api/v1/scans \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

4. **Check browser console:**
   - Open DevTools (F12)
   - Go to Console tab
   - Look for error messages
   - Check Network tab for failed requests

---

## Summary

**Problem:** Dashboard sending domain name instead of UUID
**Solution:** New `/api/v1/scans/by-domain?domain=X` endpoint
**Action:** Update dashboard delete function to use new endpoint

**New endpoint is ready to use immediately - no database migration needed!**
