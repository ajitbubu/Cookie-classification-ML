#!/usr/bin/env python3
"""
Simple scan test - no API server required
Tests the scanner directly
"""

import asyncio
import sys
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

        print("\n✅ Test PASSED")
        return True

    except Exception as e:
        print(f"❌ Scan failed: {e}")
        print("\n❌ Test FAILED")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Testing Quick Scan functionality...")
    print()

    # Check dependencies first
    try:
        from playwright_stealth import Stealth
    except ImportError:
        print("❌ ERROR: playwright_stealth not installed")
        print()
        print("Fix: Run this command:")
        print("  pip3 install playwright-stealth")
        print()
        sys.exit(1)

    # Run test
    success = asyncio.run(test_quick_scan())
    sys.exit(0 if success else 1)
