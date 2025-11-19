# Scan Delete Fix

## Problem
The frontend was unable to delete scans, showing "undefined" in the DELETE request URL:
```
DELETE /api/v1/scans/undefined HTTP/1.1" 400 Bad Request
```

## Root Cause
The backend API returns `scan_id` but the frontend TypeScript interface expects `id`. The API client was not mapping the field names correctly for scans (unlike schedules which had proper mapping).

## Solution
Updated `dashboard/lib/api.ts` to map backend field names to frontend field names for all scan-related methods:

### Changes Made:

1. **createScan()** - Maps `scan_id` → `id`, `scan_mode` → `mode`, `page_count` → `total_pages`
2. **getScans()** - Maps all scan items in the paginated response
3. **getScan()** - Maps single scan response

## How to Apply the Fix

### Option 1: Hard Refresh Browser (Recommended)
1. Open the scans page in your browser
2. Press `Cmd + Shift + R` (Mac) or `Ctrl + Shift + R` (Windows/Linux) to hard refresh
3. This will clear the cache and load the updated API code

### Option 2: Clear Browser Cache
1. Open DevTools (F12)
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"

### Option 3: Restart Next.js Dev Server
```bash
# Stop the current process (Ctrl+C in the terminal running npm run dev)
cd dashboard
npm run dev
```

## Verification

After applying the fix, you should see:
1. Scan items have an `id` field (not `scan_id`)
2. Delete button works without showing "undefined" in the URL
3. Console log shows: "API: Mapped scan items: {id: '...', domain: '...', ...}"

## Testing

You can test the API mapping with:
```bash
python test_delete_scan.py
```

This will:
1. Fetch scans and show the field structure
2. Ask for confirmation before deleting a scan
3. Verify the delete operation works

## Backend Field Mapping Reference

| Backend Field | Frontend Field |
|--------------|----------------|
| scan_id | id |
| scan_mode | mode |
| page_count | total_pages |
| (other fields remain the same) |
