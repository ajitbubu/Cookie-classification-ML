#!/usr/bin/env python3
"""
Import Cookies from Public Datasets

Imports cookie data from public sources like CookiePedia and other datasets.
Creates labeled training data for ML model improvement.

Usage:
    python scripts/import_public_datasets.py [--source SOURCE] [--output FILE]

Sources:
    - cookiepedia: Import from CookiePedia-like format
    - iab: Import from IAB GVL
    - custom: Import from custom JSON/CSV
"""

import json
import csv
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# Category mappings from various sources to our categories
CATEGORY_MAPPINGS = {
    # CookiePedia categories
    "strictly necessary": "Necessary",
    "necessary": "Necessary",
    "essential": "Necessary",
    "functional": "Functional",
    "functionality": "Functional",
    "preferences": "Functional",
    "analytics": "Analytics",
    "performance": "Analytics",
    "statistics": "Analytics",
    "advertising": "Advertising",
    "marketing": "Advertising",
    "targeting": "Advertising",
    "ad": "Advertising",

    # IAB TCF purposes
    "store_and/or_access_information": "Necessary",
    "select_basic_ads": "Advertising",
    "create_personalised_ads": "Advertising",
    "measure_ad_performance": "Analytics",
    "measure_content_performance": "Analytics",
    "apply_market_research": "Analytics",
    "develop_and_improve_products": "Functional",
}


# Known cookie datasets with their properties
KNOWN_COOKIE_DATABASE = [
    # Google Analytics
    {
        "name": "_ga",
        "vendor": "Google Analytics",
        "domain_pattern": ".google-analytics.com",
        "category": "Analytics",
        "duration": "730 days",
        "description": "Used to distinguish users",
        "third_party": True,
    },
    {
        "name": "_gid",
        "vendor": "Google Analytics",
        "domain_pattern": ".google-analytics.com",
        "category": "Analytics",
        "duration": "1 day",
        "description": "Used to distinguish users",
        "third_party": True,
    },
    {
        "name": "_gat",
        "vendor": "Google Analytics",
        "domain_pattern": ".google-analytics.com",
        "category": "Analytics",
        "duration": "1 minute",
        "description": "Used to throttle request rate",
        "third_party": True,
    },

    # Google Ads
    {
        "name": "IDE",
        "vendor": "Google DoubleClick",
        "domain_pattern": ".doubleclick.net",
        "category": "Advertising",
        "duration": "390 days",
        "description": "Used for ad serving",
        "third_party": True,
    },
    {
        "name": "test_cookie",
        "vendor": "Google DoubleClick",
        "domain_pattern": ".doubleclick.net",
        "category": "Advertising",
        "duration": "15 minutes",
        "description": "Test cookie to check if cookies are enabled",
        "third_party": True,
    },
    {
        "name": "_gcl_au",
        "vendor": "Google Ads",
        "domain_pattern": ".google.com",
        "category": "Advertising",
        "duration": "90 days",
        "description": "Used by Google AdSense for conversion tracking",
        "third_party": True,
    },

    # Facebook
    {
        "name": "_fbp",
        "vendor": "Facebook",
        "domain_pattern": ".facebook.com",
        "category": "Advertising",
        "duration": "90 days",
        "description": "Facebook pixel cookie for tracking",
        "third_party": True,
    },
    {
        "name": "_fbc",
        "vendor": "Facebook",
        "domain_pattern": ".facebook.com",
        "category": "Advertising",
        "duration": "90 days",
        "description": "Facebook click identifier",
        "third_party": True,
    },
    {
        "name": "fr",
        "vendor": "Facebook",
        "domain_pattern": ".facebook.com",
        "category": "Advertising",
        "duration": "90 days",
        "description": "Facebook advertising tracking",
        "third_party": True,
    },

    # Hotjar
    {
        "name": "_hjid",
        "vendor": "Hotjar",
        "domain_pattern": ".hotjar.com",
        "category": "Analytics",
        "duration": "365 days",
        "description": "Hotjar cookie for user tracking",
        "third_party": True,
    },
    {
        "name": "_hjSessionUser_{site_id}",
        "vendor": "Hotjar",
        "domain_pattern": ".hotjar.com",
        "category": "Analytics",
        "duration": "365 days",
        "description": "Hotjar session user cookie",
        "third_party": True,
    },

    # LinkedIn
    {
        "name": "bcookie",
        "vendor": "LinkedIn",
        "domain_pattern": ".linkedin.com",
        "category": "Advertising",
        "duration": "730 days",
        "description": "LinkedIn browser ID cookie",
        "third_party": True,
    },
    {
        "name": "lidc",
        "vendor": "LinkedIn",
        "domain_pattern": ".linkedin.com",
        "category": "Advertising",
        "duration": "1 day",
        "description": "LinkedIn routing cookie",
        "third_party": True,
    },

    # Microsoft Clarity
    {
        "name": "_clck",
        "vendor": "Microsoft Clarity",
        "domain_pattern": ".clarity.ms",
        "category": "Analytics",
        "duration": "365 days",
        "description": "Clarity user tracking",
        "third_party": True,
    },
    {
        "name": "_clsk",
        "vendor": "Microsoft Clarity",
        "domain_pattern": ".clarity.ms",
        "category": "Analytics",
        "duration": "1 day",
        "description": "Clarity session tracking",
        "third_party": True,
    },

    # Cloudflare (Necessary)
    {
        "name": "__cf_bm",
        "vendor": "Cloudflare",
        "domain_pattern": ".cloudflare.com",
        "category": "Necessary",
        "duration": "30 minutes",
        "description": "Cloudflare bot management",
        "third_party": True,
    },
    {
        "name": "_cfuvid",
        "vendor": "Cloudflare",
        "domain_pattern": ".cloudflare.com",
        "category": "Necessary",
        "duration": "Session",
        "description": "Cloudflare security cookie",
        "third_party": True,
    },

    # Generic session cookies (Necessary)
    {
        "name": "PHPSESSID",
        "vendor": "PHP",
        "domain_pattern": "",
        "category": "Necessary",
        "duration": "Session",
        "description": "PHP session identifier",
        "third_party": False,
    },
    {
        "name": "JSESSIONID",
        "vendor": "Java",
        "domain_pattern": "",
        "category": "Necessary",
        "duration": "Session",
        "description": "Java session identifier",
        "third_party": False,
    },
    {
        "name": "sessionid",
        "vendor": "Generic",
        "domain_pattern": "",
        "category": "Necessary",
        "duration": "Session",
        "description": "Generic session identifier",
        "third_party": False,
    },

    # CSRF tokens (Necessary)
    {
        "name": "csrf_token",
        "vendor": "Generic",
        "domain_pattern": "",
        "category": "Necessary",
        "duration": "Session",
        "description": "CSRF protection token",
        "third_party": False,
    },
    {
        "name": "XSRF-TOKEN",
        "vendor": "Generic",
        "domain_pattern": "",
        "category": "Necessary",
        "duration": "Session",
        "description": "Cross-site request forgery token",
        "third_party": False,
    },

    # Functional cookies
    {
        "name": "language",
        "vendor": "Generic",
        "domain_pattern": "",
        "category": "Functional",
        "duration": "365 days",
        "description": "User language preference",
        "third_party": False,
    },
    {
        "name": "currency",
        "vendor": "Generic",
        "domain_pattern": "",
        "category": "Functional",
        "duration": "30 days",
        "description": "User currency preference",
        "third_party": False,
    },
    {
        "name": "theme",
        "vendor": "Generic",
        "domain_pattern": "",
        "category": "Functional",
        "duration": "365 days",
        "description": "User theme preference (dark/light mode)",
        "third_party": False,
    },
]


def parse_duration_to_days(duration_str: str) -> float:
    """Parse duration string to days."""
    import re

    if not duration_str or duration_str.lower() == "session":
        return 0.0

    duration_lower = duration_str.lower()
    numbers = re.findall(r"\d+\.?\d*", duration_lower)

    if not numbers:
        return 0.0

    value = float(numbers[0])

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
    elif "minute" in duration_lower:
        return value / (24 * 60)
    else:
        return value


def convert_to_training_format(cookie_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert cookie data to training CSV format."""
    # Determine domain
    domain = cookie_data.get("domain_pattern", "") or cookie_data.get("domain", "")
    if not domain.startswith("."):
        domain = f".{domain}" if domain else ".example.com"

    # Parse duration
    duration_str = cookie_data.get("duration", "Session")
    duration_days = parse_duration_to_days(duration_str)

    # Determine cookie type
    is_third_party = cookie_data.get("third_party", False)
    cookie_type = "Third Party" if is_third_party else "First Party"

    # Security flags (defaults based on category and type)
    category = cookie_data.get("category", "Unknown")
    if category == "Necessary":
        httpOnly = True
        secure = True
        sameSite = "Strict"
    elif category == "Functional":
        httpOnly = False
        secure = True
        sameSite = "Lax"
    else:  # Analytics or Advertising
        httpOnly = False
        secure = True
        sameSite = "None"

    return {
        "cookie_name": cookie_data.get("name", ""),
        "domain": domain,
        "path": "/",
        "duration_days": duration_days,
        "duration_str": duration_str,
        "is_session": duration_days == 0.0,
        "httpOnly": httpOnly,
        "secure": secure,
        "sameSite": sameSite,
        "cookie_type": cookie_type,
        "size": 50,  # Estimated average size
        "set_after_accept": category != "Necessary",
        "category": category,
        "confidence": 1.0,  # High confidence for known databases
        "source": f"PublicDB_{cookie_data.get('vendor', 'Unknown')}",
    }


def import_known_database() -> List[Dict[str, Any]]:
    """Import from known cookie database."""
    print("Importing from known cookie database...")
    cookies = []

    for cookie_data in KNOWN_COOKIE_DATABASE:
        cookie = convert_to_training_format(cookie_data)
        cookies.append(cookie)

    print(f"  ✓ Imported {len(cookies)} cookies from known database")
    return cookies


def import_from_iab_gvl() -> List[Dict[str, Any]]:
    """Import cookies from IAB Global Vendor List."""
    print("Importing from IAB GVL...")

    iab_file = Path(__file__).parent.parent / "iab_gvl.json"

    if not iab_file.exists():
        print("  ⚠ IAB GVL file not found, skipping")
        return []

    try:
        with open(iab_file, 'r') as f:
            gvl_data = json.load(f)

        cookies = []
        vendors = gvl_data.get("vendors", {})

        # For each vendor, create sample cookies
        for vendor_id, vendor_info in list(vendors.items())[:50]:  # Limit to 50 vendors
            vendor_name = vendor_info.get("name", "")
            purposes = vendor_info.get("purposes", [])

            # Map IAB purposes to categories
            if 1 in purposes:  # Store and/or access information
                category = "Necessary"
            elif any(p in [7, 8, 9, 10] for p in purposes):  # Analytics purposes
                category = "Analytics"
            elif any(p in [2, 3, 4] for p in purposes):  # Ad purposes
                category = "Advertising"
            else:
                category = "Functional"

            # Create sample cookie for this vendor
            cookie = convert_to_training_format({
                "name": f"vendor_{vendor_id}",
                "vendor": vendor_name,
                "domain_pattern": ".example.com",
                "category": category,
                "duration": "365 days",
                "third_party": True,
            })

            cookies.append(cookie)

        print(f"  ✓ Imported {len(cookies)} cookies from IAB GVL")
        return cookies

    except Exception as e:
        print(f"  ✗ Error importing from IAB GVL: {e}")
        return []


def save_to_csv(cookies: List[Dict[str, Any]], output_file: Path):
    """Save cookies to CSV file."""
    if not cookies:
        print("No cookies to save!")
        return

    output_file.parent.mkdir(exist_ok=True)

    fieldnames = [
        "cookie_name", "domain", "path", "duration_days", "duration_str",
        "is_session", "httpOnly", "secure", "sameSite", "cookie_type",
        "size", "set_after_accept", "category", "confidence", "source"
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cookies)

    print(f"\n✓ Saved {len(cookies)} cookies to {output_file}")


def print_statistics(cookies: List[Dict[str, Any]]):
    """Print statistics about imported cookies."""
    if not cookies:
        return

    print(f"\n{'=' * 70}")
    print("IMPORT STATISTICS")
    print(f"{'=' * 70}")

    print(f"\nTotal cookies imported: {len(cookies)}")

    # By category
    from collections import Counter
    category_counts = Counter(c["category"] for c in cookies)
    print(f"\nBy category:")
    for category, count in sorted(category_counts.items()):
        percentage = (count / len(cookies)) * 100
        print(f"  {category:15s}: {count:4d} ({percentage:5.1f}%)")

    # By cookie type
    type_counts = Counter(c["cookie_type"] for c in cookies)
    print(f"\nBy cookie type:")
    for cookie_type, count in type_counts.items():
        percentage = (count / len(cookies)) * 100
        print(f"  {cookie_type:15s}: {count:4d} ({percentage:5.1f}%)")

    print(f"\n{'=' * 70}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Import cookies from public datasets"
    )
    parser.add_argument(
        "--source",
        "-s",
        type=str,
        default="all",
        choices=["all", "known", "iab"],
        help="Data source to import from"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="training_data/public_dataset_cookies.csv",
        help="Output CSV file path"
    )

    args = parser.parse_args()

    print(f"\n{'=' * 70}")
    print("IMPORTING COOKIES FROM PUBLIC DATASETS")
    print(f"{'=' * 70}\n")

    all_cookies = []

    # Import from selected sources
    if args.source in ["all", "known"]:
        all_cookies.extend(import_known_database())

    if args.source in ["all", "iab"]:
        all_cookies.extend(import_from_iab_gvl())

    # Print statistics
    print_statistics(all_cookies)

    # Save to CSV
    output_path = Path(args.output)
    save_to_csv(all_cookies, output_path)

    print(f"\n{'=' * 70}")
    print("NEXT STEPS")
    print(f"{'=' * 70}")
    print(f"1. Review imported cookies: {output_path}")
    print(f"2. Merge with existing training data:")
    print(f"   python scripts/merge_training_data.py")
    print(f"3. Retrain model with combined data:")
    print(f"   python scripts/train_model.py")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
