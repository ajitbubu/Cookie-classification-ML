# Quick Start - Fix Scanning Issues

## Issue: Scanning Not Working

If you're getting errors when trying to scan, follow these steps:

## Step 1: Install Missing Dependencies

```bash
# Install playwright-stealth (required for scanners)
pip3 install playwright-stealth

# Install other required packages
pip3 install playwright asyncpg apscheduler redis requests pydantic fastapi

# Install Playwright browsers
playwright install
```

## Step 2: Create a Simple Test Script

Create a file `test_scan_simple.py`:

```python
#!/usr/bin/env python3
"""
Simple scan test - no API server required
Tests the scanner directly
"""

import asyncio
from parallel_scanner import ParallelCookieScanner


async def test_quick_scan():
    """Test quick scan functionality."""
    print("🚀 Starting quick scan test...")
    print("=" * 60)

    # Create scanner
    scanner = ParallelCookieScanner(
        max_concurrent=3,
        accept_button_selector='button:has-text("Accept")'
    )

    # Test with a simple website
    domain = "https://example.com"
    custom_pages = ["/"]

    print(f"Scanning: {domain}")
    print(f"Custom pages: {custom_pages}")
    print()

    try:
        # Run scan
        result = await scanner.quick_scan(
            domain=domain,
            custom_pages=custom_pages
        )

        # Print results
        print("✅ Scan completed successfully!")
        print("=" * 60)
        print(f"Pages scanned: {result['pages_scanned']}")
        print(f"Cookies found: {result['cookies_found']}")
        print(f"Duration: {result['scan_duration']:.2f}s")
        print()

        if result['cookies']:
            print("Cookies discovered:")
            for cookie in result['cookies'][:5]:  # Show first 5
                print(f"  - {cookie['name']} ({cookie.get('domain', 'N/A')})")
            if len(result['cookies']) > 5:
                print(f"  ... and {len(result['cookies']) - 5} more")
        else:
            print("No cookies found (this is normal for example.com)")

        return True

    except Exception as e:
        print(f"❌ Scan failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_quick_scan())
    exit(0 if success else 1)
```

## Step 3: Run the Test

```bash
# Make executable
chmod +x test_scan_simple.py

# Run test
python3 test_scan_simple.py
```

## Expected Output

```
🚀 Starting quick scan test...
============================================================
Scanning: https://example.com
Custom pages: ['/']

✅ Scan completed successfully!
============================================================
Pages scanned: 1
Cookies found: 0
Duration: 2.34s

No cookies found (this is normal for example.com)
```

## Step 4: Test with Real Website

Edit `test_scan_simple.py` and change:

```python
# Test with a real website that has cookies
domain = "https://www.google.com"
custom_pages = ["/"]
```

Run again:
```bash
python3 test_scan_simple.py
```

Expected output:
```
✅ Scan completed successfully!
============================================================
Pages scanned: 1
Cookies found: 5-10
Duration: 3.45s

Cookies discovered:
  - NID (.google.com)
  - 1P_JAR (.google.com)
  - CONSENT (.google.com)
  ... and more
```

## Common Issues and Solutions

### Issue 1: "No module named 'playwright'"
**Solution:**
```bash
pip3 install playwright
playwright install
```

### Issue 2: "No module named 'playwright_stealth'"
**Solution:**
```bash
pip3 install playwright-stealth
```

### Issue 3: "Playwright executable doesn't exist"
**Solution:**
```bash
playwright install chromium
```

### Issue 4: Browser crashes or timeout
**Solution:**
```python
# Reduce concurrency
scanner = ParallelCookieScanner(
    max_concurrent=1,  # Start with 1
    timeout=60000      # Increase timeout to 60s
)
```

### Issue 5: "Permission denied" on macOS
**Solution:**
```bash
# Install Rosetta (for M1/M2 Macs)
softwareupdate --install-rosetta

# Reinstall Playwright
playwright install --force
```

## Verify Installation

Run this to check all dependencies:

```bash
python3 -c "
import sys
print(f'Python: {sys.version}')

try:
    import playwright
    print('✅ playwright')
except: print('❌ playwright - run: pip3 install playwright')

try:
    from playwright_stealth import Stealth
    print('✅ playwright_stealth')
except: print('❌ playwright_stealth - run: pip3 install playwright-stealth')

try:
    import asyncpg
    print('✅ asyncpg')
except: print('❌ asyncpg - run: pip3 install asyncpg')

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    print('✅ apscheduler')
except: print('❌ apscheduler - run: pip3 install apscheduler')

try:
    import redis
    print('✅ redis')
except: print('❌ redis - run: pip3 install redis')

print()
print('All core dependencies installed!' if all else 'Install missing dependencies above')
"
```

## Next Steps

Once scanning works:

1. ✅ Test quick scan (above)
2. ✅ Test deep scan (use EnterpriseCookieScanner)
3. ✅ Apply database migration
4. ✅ Start API server
5. ✅ Test schedule endpoints

## Quick Command Reference

```bash
# Install all dependencies at once
pip3 install playwright playwright-stealth asyncpg apscheduler redis requests pydantic fastapi uvicorn

# Install Playwright browsers
playwright install

# Test scan
python3 test_scan_simple.py

# Start API server
uvicorn api.main:app --reload

# Start scheduler
python3 -m services.enhanced_scheduler
```

## Still Not Working?

Check the detailed logs:

```python
# Add logging to see what's happening
import logging
logging.basicConfig(level=logging.DEBUG)

# Run scan again
python3 test_scan_simple.py
```

Or contact support with:
- Error message
- Python version (`python3 --version`)
- OS version
- Full stack trace
