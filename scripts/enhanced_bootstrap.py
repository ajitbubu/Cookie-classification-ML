#!/usr/bin/env python3
"""
Enhanced Bootstrap Training Data Generator

Creates comprehensive training data with variations and edge cases:
- Pattern variations (_ga, _ga_*, __ga, etc.)
- Vendor-specific cookies with variations
- Duration variations (session, short, medium, long)
- Security flag combinations
- Domain variations (first-party, third-party)
- Composite examples

This significantly expands the training dataset beyond the basic bootstrap.

Usage:
    python scripts/enhanced_bootstrap.py [--output FILE] [--multiplier N]
"""

import csv
from pathlib import Path
from typing import List, Dict, Any
import sys
import itertools

sys.path.insert(0, str(Path(__file__).parent.parent))


def generate_pattern_variations() -> List[Dict[str, Any]]:
    """Generate pattern-based cookie variations."""
    cookies = []

    # Google Analytics patterns
    ga_patterns = [
        ("_ga", "Google Analytics client ID"),
        ("_ga_*", "Google Analytics property-specific"),
        ("__ga", "Google Analytics alternate"),
        ("_gac_*", "Google Analytics campaign"),
        ("_gid", "Google Analytics session ID"),
        ("_gat", "Google Analytics throttle"),
        ("_gat_*", "Google Analytics tracker-specific throttle"),
        ("__gads", "Google Ads tracking"),
        ("__gpi", "Google Ads tracking"),
    ]

    for name, description in ga_patterns:
        cookies.append({
            "cookie_name": name,
            "domain": ".google-analytics.com",
            "path": "/",
            "duration_days": 730 if "_ga" in name else 1,
            "is_session": False,
            "httpOnly": False,
            "secure": True,
            "sameSite": "None",
            "cookie_type": "Third Party",
            "size": 50,
            "set_after_accept": True,
            "category": "Analytics",
            "confidence": 1.0,
            "source": "EnhancedBootstrap_Patterns",
        })

    # Facebook patterns
    fb_patterns = [
        ("_fbp", "Facebook pixel"),
        ("_fbc", "Facebook click ID"),
        ("fr", "Facebook tracking"),
        ("_fbq", "Facebook queue"),
        ("fbm_*", "Facebook messenger"),
        ("fbsr_*", "Facebook session"),
    ]

    for name, description in fb_patterns:
        cookies.append({
            "cookie_name": name,
            "domain": ".facebook.com",
            "path": "/",
            "duration_days": 90,
            "is_session": False,
            "httpOnly": False,
            "secure": True,
            "sameSite": "None",
            "cookie_type": "Third Party",
            "size": 50,
            "set_after_accept": True,
            "category": "Advertising",
            "confidence": 1.0,
            "source": "EnhancedBootstrap_Patterns",
        })

    # Session ID patterns
    session_patterns = [
        ("PHPSESSID", ".example.com", "Necessary"),
        ("JSESSIONID", ".example.com", "Necessary"),
        ("ASP.NET_SessionId", ".example.com", "Necessary"),
        ("sessionid", ".example.com", "Necessary"),
        ("session_id", ".example.com", "Necessary"),
        ("sid", ".example.com", "Necessary"),
        ("s_id", ".example.com", "Necessary"),
    ]

    for name, domain, category in session_patterns:
        cookies.append({
            "cookie_name": name,
            "domain": domain,
            "path": "/",
            "duration_days": 0,
            "is_session": True,
            "httpOnly": True,
            "secure": True,
            "sameSite": "Strict",
            "cookie_type": "First Party",
            "size": 32,
            "set_after_accept": False,
            "category": category,
            "confidence": 1.0,
            "source": "EnhancedBootstrap_Patterns",
        })

    return cookies


def generate_vendor_variations() -> List[Dict[str, Any]]:
    """Generate vendor-specific cookie variations."""
    cookies = []

    # Advertising vendors
    ad_vendors = [
        ("IDE", ".doubleclick.net", "Google DoubleClick"),
        ("test_cookie", ".doubleclick.net", "Google DoubleClick"),
        ("DSID", ".doubleclick.net", "Google DoubleClick"),
        ("__gads", ".google.com", "Google Ads"),
        ("_gcl_au", ".google.com", "Google Ads conversion"),
        ("_gcl_aw", ".google.com", "Google Ads remarketing"),
        ("_gcl_gb", ".google.com", "Google Ads linker"),
        ("bcookie", ".linkedin.com", "LinkedIn ads"),
        ("bscookie", ".linkedin.com", "LinkedIn secure"),
        ("lidc", ".linkedin.com", "LinkedIn routing"),
        ("UserMatchHistory", ".linkedin.com", "LinkedIn matching"),
        ("AnalyticsSyncHistory", ".linkedin.com", "LinkedIn analytics sync"),
    ]

    for name, domain, vendor in ad_vendors:
        cookies.append({
            "cookie_name": name,
            "domain": domain,
            "path": "/",
            "duration_days": 390,
            "is_session": False,
            "httpOnly": False,
            "secure": True,
            "sameSite": "None",
            "cookie_type": "Third Party",
            "size": 50,
            "set_after_accept": True,
            "category": "Advertising",
            "confidence": 1.0,
            "source": f"EnhancedBootstrap_{vendor.replace(' ', '')}",
        })

    # Analytics vendors
    analytics_vendors = [
        ("_hjid", ".hotjar.com", "Hotjar"),
        ("_hjSessionUser_*", ".hotjar.com", "Hotjar"),
        ("_hjSession_*", ".hotjar.com", "Hotjar"),
        ("_hjIncludedInPageviewSample", ".hotjar.com", "Hotjar"),
        ("_clck", ".clarity.ms", "Microsoft Clarity"),
        ("_clsk", ".clarity.ms", "Microsoft Clarity"),
        ("_cltk", ".clarity.ms", "Microsoft Clarity"),
        ("MUID", ".bing.com", "Microsoft Bing"),
        ("_uetsid", ".bing.com", "Bing UET"),
        ("_uetvid", ".bing.com", "Bing UET"),
    ]

    for name, domain, vendor in analytics_vendors:
        cookies.append({
            "cookie_name": name,
            "domain": domain,
            "path": "/",
            "duration_days": 365,
            "is_session": False,
            "httpOnly": False,
            "secure": True,
            "sameSite": "None",
            "cookie_type": "Third Party",
            "size": 50,
            "set_after_accept": True,
            "category": "Analytics",
            "confidence": 1.0,
            "source": f"EnhancedBootstrap_{vendor.replace(' ', '')}",
        })

    return cookies


def generate_duration_variations() -> List[Dict[str, Any]]:
    """Generate cookies with different duration patterns."""
    cookies = []

    # Duration patterns: (days, name_suffix, description)
    durations = [
        (0, "session", "Session cookie"),
        (0.04, "1hour", "1 hour cookie"),  # 1/24 day
        (0.5, "12hour", "12 hour cookie"),
        (1, "1day", "1 day cookie"),
        (7, "1week", "1 week cookie"),
        (30, "1month", "1 month cookie"),
        (90, "3month", "3 months cookie"),
        (365, "1year", "1 year cookie"),
        (730, "2year", "2 years cookie"),
    ]

    categories = ["Necessary", "Functional", "Analytics", "Advertising"]

    for duration_days, duration_name, description in durations:
        for category in categories:
            cookies.append({
                "cookie_name": f"test_{category.lower()}_{duration_name}",
                "domain": ".example.com",
                "path": "/",
                "duration_days": duration_days,
                "is_session": duration_days == 0,
                "httpOnly": category == "Necessary",
                "secure": True,
                "sameSite": "Strict" if category == "Necessary" else "Lax" if category == "Functional" else "None",
                "cookie_type": "First Party" if category in ["Necessary", "Functional"] else "Third Party",
                "size": 50,
                "set_after_accept": category != "Necessary",
                "category": category,
                "confidence": 1.0,
                "source": "EnhancedBootstrap_Duration",
            })

    return cookies


def generate_security_variations() -> List[Dict[str, Any]]:
    """Generate cookies with different security flag combinations."""
    cookies = []

    # Security combinations
    security_combos = [
        (True, True, "Strict", "Necessary"),
        (True, True, "Lax", "Functional"),
        (False, True, "Lax", "Functional"),
        (False, True, "None", "Analytics"),
        (False, True, "None", "Advertising"),
        (False, False, "None", "Advertising"),  # Insecure ad cookie
    ]

    for i, (http_only, secure, same_site, category) in enumerate(security_combos):
        cookies.append({
            "cookie_name": f"security_test_{i}",
            "domain": ".example.com",
            "path": "/",
            "duration_days": 30,
            "is_session": False,
            "httpOnly": http_only,
            "secure": secure,
            "sameSite": same_site,
            "cookie_type": "First Party",
            "size": 50,
            "set_after_accept": category != "Necessary",
            "category": category,
            "confidence": 1.0,
            "source": "EnhancedBootstrap_Security",
        })

    return cookies


def generate_functional_variations() -> List[Dict[str, Any]]:
    """Generate functional cookie variations."""
    cookies = []

    functional_patterns = [
        ("language", "Language preference"),
        ("lang", "Language preference"),
        ("locale", "Locale preference"),
        ("currency", "Currency preference"),
        ("theme", "Theme preference"),
        ("dark_mode", "Dark mode preference"),
        ("sidebar_state", "Sidebar state"),
        ("view_mode", "View mode preference"),
        ("timezone", "Timezone preference"),
        ("cookie_consent", "Cookie consent status"),
        ("consent_preferences", "Consent preferences"),
        ("privacy_settings", "Privacy settings"),
    ]

    for name, description in functional_patterns:
        cookies.append({
            "cookie_name": name,
            "domain": ".example.com",
            "path": "/",
            "duration_days": 365,
            "is_session": False,
            "httpOnly": False,
            "secure": True,
            "sameSite": "Lax",
            "cookie_type": "First Party",
            "size": 20,
            "set_after_accept": False,
            "category": "Functional",
            "confidence": 1.0,
            "source": "EnhancedBootstrap_Functional",
        })

    return cookies


def generate_edge_cases() -> List[Dict[str, Any]]:
    """Generate edge case cookies."""
    cookies = []

    # CSRF tokens (Necessary)
    csrf_patterns = [
        "csrf_token", "csrftoken", "_csrf", "XSRF-TOKEN",
        "csrf", "xsrf", "anti-csrf", "request_token"
    ]

    for name in csrf_patterns:
        cookies.append({
            "cookie_name": name,
            "domain": ".example.com",
            "path": "/",
            "duration_days": 0,
            "is_session": True,
            "httpOnly": True,
            "secure": True,
            "sameSite": "Strict",
            "cookie_type": "First Party",
            "size": 32,
            "set_after_accept": False,
            "category": "Necessary",
            "confidence": 1.0,
            "source": "EnhancedBootstrap_EdgeCase",
        })

    # Load balancer cookies (Necessary)
    lb_patterns = [
        ("awsalb", "AWS ALB"),
        ("awsalbcors", "AWS ALB CORS"),
        ("lb_cookie", "Load balancer"),
        ("server_id", "Server ID"),
    ]

    for name, description in lb_patterns:
        cookies.append({
            "cookie_name": name,
            "domain": ".example.com",
            "path": "/",
            "duration_days": 7,
            "is_session": False,
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax",
            "cookie_type": "First Party",
            "size": 50,
            "set_after_accept": False,
            "category": "Necessary",
            "confidence": 1.0,
            "source": "EnhancedBootstrap_EdgeCase",
        })

    # Authentication cookies (Necessary)
    auth_patterns = [
        "auth_token", "access_token", "refresh_token",
        "remember_token", "auth_session", "user_session",
        "login_token", "jwt", "bearer_token"
    ]

    for name in auth_patterns:
        cookies.append({
            "cookie_name": name,
            "domain": ".example.com",
            "path": "/",
            "duration_days": 30,
            "is_session": False,
            "httpOnly": True,
            "secure": True,
            "sameSite": "Strict",
            "cookie_type": "First Party",
            "size": 100,
            "set_after_accept": False,
            "category": "Necessary",
            "confidence": 1.0,
            "source": "EnhancedBootstrap_EdgeCase",
        })

    return cookies


def generate_all_variations() -> List[Dict[str, Any]]:
    """Generate all cookie variations."""
    all_cookies = []

    print("Generating enhanced bootstrap data...")

    generators = [
        ("Pattern variations", generate_pattern_variations),
        ("Vendor variations", generate_vendor_variations),
        ("Duration variations", generate_duration_variations),
        ("Security variations", generate_security_variations),
        ("Functional variations", generate_functional_variations),
        ("Edge cases", generate_edge_cases),
    ]

    for name, generator_func in generators:
        cookies = generator_func()
        all_cookies.extend(cookies)
        print(f"  ✓ {name}: {len(cookies)} cookies")

    return all_cookies


def save_to_csv(cookies: List[Dict[str, Any]], output_file: Path):
    """Save cookies to CSV file."""
    output_file.parent.mkdir(exist_ok=True)

    fieldnames = [
        "cookie_name", "domain", "path", "duration_days",
        "is_session", "httpOnly", "secure", "sameSite", "cookie_type",
        "size", "set_after_accept", "category", "confidence", "source"
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cookies)

    print(f"\n✓ Saved {len(cookies)} cookies to {output_file}")


def print_statistics(cookies: List[Dict[str, Any]]):
    """Print statistics about generated cookies."""
    from collections import Counter

    print(f"\n{'=' * 70}")
    print("ENHANCED BOOTSTRAP STATISTICS")
    print(f"{'=' * 70}")

    print(f"\nTotal cookies: {len(cookies)}")

    # By category
    category_counts = Counter(c["category"] for c in cookies)
    print(f"\nBy category:")
    for category, count in sorted(category_counts.items()):
        percentage = (count / len(cookies)) * 100
        print(f"  {category:15s}: {count:4d} ({percentage:5.1f}%)")

    # By source
    source_counts = Counter(c["source"] for c in cookies)
    print(f"\nBy source:")
    for source, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        percentage = (count / len(cookies)) * 100
        print(f"  {source:35s}: {count:4d} ({percentage:5.1f}%)")

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
        description="Generate enhanced bootstrap training data with variations"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="training_data/enhanced_bootstrap_cookies.csv",
        help="Output CSV file path"
    )

    args = parser.parse_args()

    print(f"\n{'=' * 70}")
    print("ENHANCED BOOTSTRAP TRAINING DATA GENERATOR")
    print(f"{'=' * 70}\n")

    # Generate all variations
    cookies = generate_all_variations()

    # Print statistics
    print_statistics(cookies)

    # Save to CSV
    output_path = Path(args.output)
    save_to_csv(cookies, output_path)

    print(f"\n{'=' * 70}")
    print("NEXT STEPS")
    print(f"{'=' * 70}")
    print(f"1. Review generated cookies: {output_path}")
    print(f"2. Merge with other training data:")
    print(f"   python scripts/merge_training_data.py")
    print(f"3. Retrain model with more data:")
    print(f"   python scripts/train_model.py")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
