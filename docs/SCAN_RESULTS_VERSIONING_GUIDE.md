# Scan Results & Versioning System - Complete Guide

## Overview

A comprehensive scan results and versioning system has been implemented for the cookie scanner dashboard. This system allows users to:

- **View detailed scan results** with all cookie information
- **Track scan versions** for each domain
- **Browse cookie details** with ML classification, categories, and security attributes
- **Compare scans** across different versions
- **Analyze statistics** including category distribution and security metrics

---

## ✨ New Features

### 1. **Detailed Scan Results View**
- Comprehensive display of all scan data
- Tabbed interface for different data views
- Real-time statistics and charts

### 2. **Scan Versioning**
- Each domain maintains a version history of scans
- Easy switching between different scan versions
- Version comparison capabilities

### 3. **Cookie Details Table**
- Expandable rows for detailed cookie information
- Filter by category and cookie type
- ML classification probabilities displayed
- Security attributes highlighted

### 4. **Statistics Dashboard**
- Cookie distribution by category
- Security features analysis
- ML classification quality metrics

---

## 🎯 How to Use

### Viewing Scan Results

1. **Navigate to Scans Page**
   - Go to Dashboard → Scans

2. **Find Completed Scan**
   - Look for scans with status "completed"
   - A green magnifying glass icon appears in the Actions column

3. **Click "View Results" Button**
   - Click the 🔍 icon to open detailed results
   - Modal opens with full scan information

### Exploring Results

The results view has **4 tabs**:

#### Tab 1: Cookies
- **Filter cookies** by category (Necessary, Functional, Analytics, Advertising)
- **Filter by type** (First Party, Third Party)
- **Expand rows** to see detailed information:
  - Description
  - ML classification probabilities
  - Classification evidence
  - IAB TCF purposes
  - Technical details

#### Tab 2: Statistics
- **Category Distribution**: Visual breakdown of cookies by category
- **Security Features**: Count of Secure, HttpOnly, and SameSite flags
- **ML Classification Quality**: High/Medium/Low confidence distribution

#### Tab 3: Pages Visited
- Complete list of all pages scanned
- URLs displayed in monospace font for clarity

#### Tab 4: Storage
- **Local Storage** entries
- **Session Storage** entries
- Key-value pairs displayed in tables

### Version Management

#### Viewing Different Versions

1. **Version Selector**
   - Located at the top of the results modal
   - Shows all scans for the current domain
   - Sorted by date (newest first)

2. **Switch Between Versions**
   - Select a version from the dropdown
   - Results update automatically
   - Version number displayed as badge

3. **Version Indicator**
   - Each scan shows its version number
   - Format: "Version X" (e.g., Version 1, Version 2)
   - Latest scan is the highest version number

---

## 📊 Data Displayed

### Scan Summary

At the top of the results view:

| Metric | Description |
|--------|-------------|
| **Total Cookies** | Total number of cookies found |
| **Pages Scanned** | Number of pages visited |
| **Third Party** | Count of third-party cookies |
| **Need Review** | Cookies requiring manual review (low ML confidence) |

### Cookie Details

Each cookie row shows:

| Field | Description |
|-------|-------------|
| **Name** | Cookie name (⚠️ if requires review) |
| **Domain** | Cookie domain |
| **Type** | First Party / Third Party |
| **Vendor** | Cookie provider/vendor |
| **Duration** | Cookie lifespan (e.g., "30 days", "Session") |
| **Security** | Secure, HttpOnly, SameSite flags |
| **Confidence** | ML classification confidence (0-100%) |
| **Source** | Classification source (DB, ML_High, ML_Low, IAB, etc.) |

### Expanded Cookie Information

Click any cookie row to expand and see:

#### Description
Human-readable explanation of the cookie's purpose

#### ML Classification Probabilities
Visual chart showing probability distribution across all categories:
- Necessary
- Functional
- Analytics
- Advertising

#### Classification Evidence
Bullet-point list of reasons for the classification

#### IAB TCF Purposes
Interactive Advertising Bureau Transparency & Consent Framework purposes

#### Technical Details
- **Path**: Cookie path
- **Size**: Size in bytes
- **Set After Accept**: Whether set after consent
- **Value Hash**: SHA-256 hash (truncated for display)

---

## 🎨 Visual Indicators

### Category Colors

| Category | Color | Badge |
|----------|-------|-------|
| **Necessary** | Red | 🔴 Critical |
| **Functional** | Blue | 🔵 Feature |
| **Analytics** | Yellow | 🟡 Tracking |
| **Advertising** | Purple | 🟣 Marketing |
| **Uncategorized** | Gray | ⚪ Unknown |

### Confidence Levels

| Confidence | Color | Range |
|------------|-------|-------|
| **High** | Green | ≥ 80% |
| **Medium** | Yellow | 60-79% |
| **Low** | Red | < 60% |

### Cookie Type Badges

- **First Party**: Green badge
- **Third Party**: Orange badge

### Security Icons

- 🛡️ **Secure Flag**: Green shield icon
- **HttpOnly**: Blue badge
- **SameSite**: Purple badge

---

## 🔍 Filtering and Search

### Category Filter
- Dropdown menu with all available categories
- Shows count of cookies in each category
- "All Categories" option to clear filter

### Type Filter
- Filter by First Party or Third Party
- "All Types" to see everything

### Dynamic Count
- Shows "X / Total" filtered vs total cookies
- Updates in real-time as you filter

---

## 📈 Statistics Tab Features

### 1. Cookie Distribution by Category

Visual bar chart showing:
- Number of cookies in each category
- Percentage of total
- Color-coded bars matching category colors

### 2. Security Features Analysis

Grid display showing count of cookies with:
- **Secure Flag**: HTTPS-only cookies
- **HttpOnly Flag**: JavaScript-inaccessible cookies
- **SameSite Set**: Cross-site request protection

### 3. ML Classification Quality

Four-box grid showing:
- **High Confidence (≥80%)**: Green box - Reliable classifications
- **Medium Confidence (60-79%)**: Yellow box - May need review
- **Low Confidence (<60%)**: Red box - Should be reviewed
- **Requires Review**: Gray box - Flagged for manual review

---

## 🔄 Version Comparison Workflow

### Comparing Two Scans

1. **Open Results** for latest scan
2. **Note the metrics** (cookies count, categories, etc.)
3. **Switch version** using dropdown
4. **Compare changes**:
   - Did new cookies appear?
   - Were cookies removed?
   - Did categories change?

### Use Cases for Versioning

- **Track cookie changes** over time
- **Monitor compliance** after website updates
- **Audit cookie policies** before/after consent implementation
- **Investigate issues** by comparing working vs broken states

---

## 🛠️ Technical Implementation

### New Components Created

#### 1. **CookieDetailsTable.tsx**
Location: `dashboard/components/scans/CookieDetailsTable.tsx`

Features:
- Expandable rows
- Category-based grouping
- Filtering capabilities
- ML probability visualization

#### 2. **ScanResultsView.tsx**
Location: `dashboard/components/scans/ScanResultsView.tsx`

Features:
- Tabbed interface
- Version selector
- Statistics charts
- Storage viewer

### Updated Files

#### 1. **types/index.ts**
Added comprehensive types:
```typescript
export interface Cookie {
  cookie_id: string;
  name: string;
  category?: string;
  ml_confidence?: number;
  ml_probabilities?: Record<string, number>;
  classification_evidence?: string[];
  requires_review: boolean;
  // ... and 20+ more fields
}

export interface ScanResult {
  scan_id: string;
  cookies: Cookie[];
  version?: number;
  pages_visited: string[];
  storages?: {
    localStorage: Record<string, string>;
    sessionStorage: Record<string, string>;
  };
  // ... more fields
}
```

#### 2. **lib/api.ts**
Added new API method:
```typescript
async getScanResult(scanId: string): Promise<ScanResult>
```

#### 3. **app/dashboard/scans/page.tsx**
Added:
- Import for `ScanResultsView` component
- State for results modal
- "View Results" button for completed scans
- Results modal integration

---

## 🚀 Getting Started

### For Users

1. **Run a scan**:
   - Click "New Scan"
   - Enter domain (e.g., "https://example.com")
   - Choose Quick or Deep scan
   - Click "Create Scan"

2. **Wait for completion**:
   - Watch real-time progress
   - See pages scanned and cookies found

3. **View results**:
   - Click green 🔍 icon when scan completes
   - Explore cookies, statistics, and pages

### For Developers

#### Run the Dashboard

```bash
cd dashboard
npm install
npm run dev
```

Navigate to: `http://localhost:3000/dashboard/scans`

#### Backend Requirements

Ensure the API returns ScanResult with all fields:
- `scan_id`
- `cookies` array with full Cookie objects
- `pages_visited` array
- `storages` object
- `version` (optional but recommended)

---

## 💡 Tips and Best Practices

### For Better Results

1. **Run scans regularly** to track cookie changes
2. **Review low-confidence classifications** manually
3. **Check third-party cookies** for compliance
4. **Monitor required security flags** (Secure, HttpOnly, SameSite)

### Performance Tips

1. **Filter before expanding** - Use category/type filters to narrow down cookies
2. **Close modals** when done - Frees up browser memory
3. **Use Quick scan** for faster results if you don't need deep crawling

### Compliance Workflow

1. **Scan your site** before implementing consent
2. **Note all cookies** and their categories
3. **Implement consent** banner
4. **Scan again** to verify cookies are blocked
5. **Compare versions** to ensure compliance

---

## 🐛 Troubleshooting

### "No cookies found"

**Possible causes:**
- Website has no cookies
- Cookie consent banner blocked cookies
- Scan failed before completion

**Solutions:**
- Check scan status (should be "completed")
- Re-run scan with different parameters
- Check if website actually sets cookies

### "Failed to load scan results"

**Possible causes:**
- Scan ID doesn't exist
- Network error
- Backend not running

**Solutions:**
- Refresh the page
- Check browser console for errors
- Verify API is running (`http://localhost:8000/api/v1/health`)

### Version selector is empty

**Cause:**
- Only one scan exists for this domain

**Solution:**
- Run more scans for the same domain to create versions
- Each new scan increments the version number

### ML confidence is always 0%

**Cause:**
- ML classification not enabled
- Cookies classified by database lookup only

**Solution:**
- Enable ML classification in backend config
- Run scan again after enabling ML

---

## 📝 Examples

### Example 1: Basic Scan Review

```
1. Navigate to Scans page
2. Click "New Scan"
3. Enter domain: "https://example.com"
4. Select "Quick Scan"
5. Click "Create Scan"
6. Wait for "completed" status
7. Click 🔍 icon
8. Review cookies in "Cookies" tab
9. Check statistics in "Statistics" tab
```

### Example 2: Comparing Versions

```
1. Open results for latest scan (Version 3)
2. Note: 45 cookies total, 12 advertising
3. Select "Version 2" from dropdown
4. Note: 50 cookies total, 15 advertising
5. Conclusion: 5 advertising cookies were removed
```

### Example 3: Finding Third-Party Cookies

```
1. Open scan results
2. Go to "Cookies" tab
3. Filter "Cookie Type" → "Third Party"
4. See filtered list of third-party cookies
5. Expand each to see vendor and purpose
```

---

## 🔒 Security & Privacy

### Data Handling

- **Cookie values are hashed** (SHA-256) for privacy
- **No plain-text storage** of sensitive cookie data
- **Local storage/session storage** shown for debugging only

### Compliance Features

- **Category classification** for GDPR compliance
- **IAB TCF purpose** mapping
- **Vendor identification** for transparency
- **First/third-party distinction** for disclosure

---

## 📚 Related Documentation

- [Three-Tier Scanning System](THREE_TIER_SCANNING_SYSTEM.md)
- [ML Cookie Classification](ML_CLASSIFICATION_GUIDE.md)
- [API Documentation](API_DOCS.md)
- [Dashboard User Guide](dashboard/USER_GUIDE.md)

---

## 🎉 Summary

You now have a complete scan results and versioning system that provides:

✅ **Detailed cookie information** with ML classification
✅ **Version tracking** for each domain
✅ **Visual statistics** and charts
✅ **Filtering and search** capabilities
✅ **Security attribute** highlighting
✅ **Compliance-ready** categorization

**Next Steps:**
1. Run your first scan
2. Explore the detailed results
3. Track changes over multiple scans
4. Use the data for compliance reporting

Enjoy your enhanced cookie scanning experience! 🍪
