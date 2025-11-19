#!/usr/bin/env python3
"""
Cookie Collection Script for Popular Websites

Scans popular websites to collect real-world cookie data for ML training.
Extracts cookies with all properties needed for classification.

Usage:
    python scripts/collect_cookies_from_websites.py [--output FILE] [--limit N]
"""

import asyncio
import json
import csv
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from playwright.async_api import async_playwright
import hashlib

# Add parent directory to path
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# Popular websites across different categories
POPULAR_WEBSITES = [
    # News & Media
    "https://www.cnn.com",
    "https://www.bbc.com",
    "https://www.theguardian.com",
    "https://www.nytimes.com",

    # E-commerce
    "https://www.amazon.com",
    "https://www.ebay.com",
    "https://www.walmart.com",

    # Social Media
    "https://www.facebook.com",
    "https://www.twitter.com",
    "https://www.linkedin.com",
    "https://www.instagram.com",

    # Technology
    "https://www.github.com",
    "https://www.stackoverflow.com",
    "https://www.microsoft.com",

    # Entertainment
    "https://www.youtube.com",
    "https://www.netflix.com",
    "https://www.spotify.com",

    # Search Engines
    "https://www.google.com",
    "https://www.bing.com",

    # Travel
    "https://www.booking.com",
    "https://www.airbnb.com",

    # Finance
    "https://www.paypal.com",
    "https://www.stripe.com",
]


def cookie_duration_days(expiry_ts):
    """Convert expiry timestamp to human-readable duration."""
    if not expiry_ts or expiry_ts == -1:
        return "Session"

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    expiry = datetime.fromtimestamp(expiry_ts, timezone.utc)

    if expiry <= now:
        return "Expired"

    days = (expiry - now).days

    if days < 1:
        hours = (expiry - now).seconds // 3600
        return f"{hours} hours"
    elif days < 30:
        return f"{days} days"
    elif days < 365:
        months = days // 30
        return f"{months} months"
    else:
        years = days // 365
        return f"{years} years"


async def collect_cookies_from_url(url: str, headless: bool = True) -> List[Dict[str, Any]]:
    """
    Collect cookies from a single URL.

    Args:
        url: Website URL to scan
        headless: Run browser in headless mode

    Returns:
        List of cookie dictionaries
    """
    cookies_collected = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

            page = await context.new_page()

            print(f"  Navigating to {url}...")
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(3000)  # Wait 3 seconds for dynamic content
            except Exception as e:
                print(f"  ⚠ Navigation warning: {e}")
                # Continue anyway, might have partial data

            # Try to accept cookie banner if present
            try:
                # Common accept button selectors
                accept_selectors = [
                    'button:has-text("Accept")',
                    'button:has-text("Accept all")',
                    'button:has-text("I agree")',
                    'button:has-text("Agree")',
                    '[data-testid="accept-button"]',
                    '.cookie-accept',
                    '#accept-cookies',
                ]

                for selector in accept_selectors:
                    try:
                        await page.click(selector, timeout=2000)
                        print(f"  ✓ Clicked accept button")
                        await page.wait_for_timeout(2000)
                        break
                    except:
                        continue
            except Exception:
                pass  # No cookie banner or couldn't click

            # Collect cookies
            cookies = await context.cookies()

            # Parse domain from URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            base_domain = parsed.netloc

            for cookie in cookies:
                cookie_dict = {
                    "name": cookie.get("name"),
                    "domain": cookie.get("domain"),
                    "path": cookie.get("path", "/"),
                    "cookie_duration": cookie_duration_days(cookie.get("expires")),
                    "duration_days": _parse_duration_to_days(cookie_duration_days(cookie.get("expires"))),
                    "is_session": not cookie.get("expires") or cookie.get("expires") == -1,
                    "httpOnly": cookie.get("httpOnly", False),
                    "secure": cookie.get("secure", False),
                    "sameSite": cookie.get("sameSite", "None"),
                    "cookie_type": _determine_cookie_type(cookie.get("domain", ""), base_domain),
                    "size": len(cookie.get("value", "")),
                    "source_url": url,
                    "collected_at": datetime.utcnow().isoformat(),
                }
                cookies_collected.append(cookie_dict)

            print(f"  ✓ Collected {len(cookies_collected)} cookies")

            await browser.close()

    except Exception as e:
        print(f"  ✗ Error collecting from {url}: {e}")

    return cookies_collected


def _determine_cookie_type(cookie_domain: str, site_domain: str) -> str:
    """Determine if cookie is first-party or third-party."""
    cookie_domain = cookie_domain.lstrip(".").lower()
    site_domain = site_domain.lstrip(".").lower()

    # Extract base domain
    def get_base_domain(domain):
        parts = domain.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return domain

    cookie_base = get_base_domain(cookie_domain)
    site_base = get_base_domain(site_domain)

    return "First Party" if cookie_base == site_base else "Third Party"


def _parse_duration_to_days(duration_str: str) -> float:
    """Parse duration string to days."""
    if not duration_str or duration_str.lower() == "session":
        return 0.0

    duration_lower = duration_str.lower()

    # Extract number
    import re
    numbers = re.findall(r"\d+\.?\d*", duration_lower)
    if not numbers:
        return 0.0

    value = float(numbers[0])

    # Determine unit
    if "year" in duration_lower:
        return value * 365
    elif "month" in duration_lower:
        return value * 30
    elif "week" in duration_lower:
        return value * 7
    elif "day" in duration_lower:
        return value
    elif "hour" in duration_lower:
        return value / 24
    else:
        return value


async def collect_from_all_websites(
    websites: List[str],
    limit: int = None,
    headless: bool = True
) -> List[Dict[str, Any]]:
    """
    Collect cookies from multiple websites.

    Args:
        websites: List of website URLs
        limit: Maximum number of websites to scan
        headless: Run browser in headless mode

    Returns:
        List of all collected cookies
    """
    all_cookies = []

    websites_to_scan = websites[:limit] if limit else websites

    print(f"\n{'=' * 70}")
    print(f"COLLECTING COOKIES FROM {len(websites_to_scan)} WEBSITES")
    print(f"{'=' * 70}\n")

    for i, url in enumerate(websites_to_scan, 1):
        print(f"[{i}/{len(websites_to_scan)}] Scanning: {url}")
        cookies = await collect_cookies_from_url(url, headless)
        all_cookies.extend(cookies)
        print()

        # Small delay between requests
        await asyncio.sleep(2)

    return all_cookies


def save_to_csv(cookies: List[Dict[str, Any]], output_file: Path):
    """Save collected cookies to CSV file."""
    if not cookies:
        print("No cookies to save!")
        return

    # Ensure directory exists
    output_file.parent.mkdir(exist_ok=True)

    fieldnames = [
        "name", "domain", "path", "cookie_duration", "duration_days",
        "is_session", "httpOnly", "secure", "sameSite", "cookie_type",
        "size", "source_url", "collected_at", "category", "confidence", "source"
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for cookie in cookies:
            # Add empty category fields for manual labeling
            cookie.setdefault("category", "")
            cookie.setdefault("confidence", "")
            cookie.setdefault("source", "WebScrape")
            writer.writerow(cookie)

    print(f"✓ Saved {len(cookies)} cookies to {output_file}")


def print_statistics(cookies: List[Dict[str, Any]]):
    """Print statistics about collected cookies."""
    if not cookies:
        return

    print(f"\n{'=' * 70}")
    print("COLLECTION STATISTICS")
    print(f"{'=' * 70}")

    print(f"\nTotal cookies collected: {len(cookies)}")

    # Unique cookies (by name + domain)
    unique = set((c["name"], c["domain"]) for c in cookies)
    print(f"Unique cookies: {len(unique)}")

    # By cookie type
    first_party = sum(1 for c in cookies if c["cookie_type"] == "First Party")
    third_party = sum(1 for c in cookies if c["cookie_type"] == "Third Party")
    print(f"\nCookie types:")
    print(f"  First Party:  {first_party} ({first_party/len(cookies)*100:.1f}%)")
    print(f"  Third Party:  {third_party} ({third_party/len(cookies)*100:.1f}%)")

    # By duration
    session = sum(1 for c in cookies if c["is_session"])
    persistent = len(cookies) - session
    print(f"\nDuration:")
    print(f"  Session:     {session} ({session/len(cookies)*100:.1f}%)")
    print(f"  Persistent:  {persistent} ({persistent/len(cookies)*100:.1f}%)")

    # Security flags
    http_only = sum(1 for c in cookies if c["httpOnly"])
    secure = sum(1 for c in cookies if c["secure"])
    print(f"\nSecurity:")
    print(f"  HttpOnly:    {http_only} ({http_only/len(cookies)*100:.1f}%)")
    print(f"  Secure:      {secure} ({secure/len(cookies)*100:.1f}%)")

    # Top domains
    from collections import Counter
    domain_counts = Counter(c["domain"] for c in cookies)
    print(f"\nTop 10 domains:")
    for domain, count in domain_counts.most_common(10):
        print(f"  {domain:40s}: {count}")

    print(f"\n{'=' * 70}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Collect cookies from popular websites for ML training"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="training_data/collected_cookies.csv",
        help="Output CSV file path"
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="Maximum number of websites to scan"
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Run browser in visible mode (not headless)"
    )
    parser.add_argument(
        "--custom-urls",
        type=str,
        help="Comma-separated list of custom URLs to scan"
    )

    args = parser.parse_args()

    # Use custom URLs if provided
    if args.custom_urls:
        websites = [url.strip() for url in args.custom_urls.split(",")]
    else:
        websites = POPULAR_WEBSITES

    # Collect cookies
    cookies = asyncio.run(
        collect_from_all_websites(
            websites,
            limit=args.limit,
            headless=not args.visible
        )
    )

    # Print statistics
    print_statistics(cookies)

    # Save to CSV
    output_path = Path(args.output)
    save_to_csv(cookies, output_path)

    print(f"\n{'=' * 70}")
    print("NEXT STEPS")
    print(f"{'=' * 70}")
    print(f"1. Review collected cookies: {output_path}")
    print(f"2. Label categories manually (Necessary/Functional/Analytics/Advertising)")
    print(f"3. Merge with existing training data:")
    print(f"   python scripts/merge_training_data.py")
    print(f"4. Retrain model with more data:")
    print(f"   python scripts/train_model.py")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
