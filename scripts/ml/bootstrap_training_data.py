"""
Bootstrap Training Data Script

Extracts training data from:
1. cookie_rules.json (existing rule patterns)
2. IAB GVL (vendor mappings)
3. Synthetic cookie generation
4. Known public cookie datasets

Generates labeled_cookies.csv for ML model training.
"""

import json
import csv
import re
from pathlib import Path
from typing import List, Dict, Any
import random

# Base directory
BASE_DIR = Path(__file__).parent.parent
COOKIE_RULES_FILE = BASE_DIR / "cookie_rules.json"
IAB_GVL_FILE = BASE_DIR / "iab_gvl.json"
OUTPUT_FILE = BASE_DIR / "training_data" / "labeled_cookies.csv"

# Category mapping
CATEGORY_MAP = {
    "necessary": "Necessary",
    "functional": "Functional",
    "analytics": "Analytics",
    "marketing": "Advertising",
    "advertising": "Advertising",
    "unknown": None,  # Skip unknown for training
}

# Known cookie datasets (manually curated from public sources)
KNOWN_COOKIES = [
    # Google Analytics
    {"name": "_ga", "domain": ".google-analytics.com", "duration_days": 730, "category": "Analytics", "vendor": "Google"},
    {"name": "_gid", "domain": ".google-analytics.com", "duration_days": 1, "category": "Analytics", "vendor": "Google"},
    {"name": "_gat", "domain": ".google-analytics.com", "duration_days": 1, "category": "Analytics", "vendor": "Google"},
    {"name": "_gac_UA-*", "domain": ".google-analytics.com", "duration_days": 90, "category": "Analytics", "vendor": "Google"},

    # Facebook
    {"name": "_fbp", "domain": ".facebook.com", "duration_days": 90, "category": "Advertising", "vendor": "Facebook"},
    {"name": "_fbc", "domain": ".facebook.com", "duration_days": 90, "category": "Advertising", "vendor": "Facebook"},
    {"name": "fr", "domain": ".facebook.com", "duration_days": 90, "category": "Advertising", "vendor": "Facebook"},
    {"name": "datr", "domain": ".facebook.com", "duration_days": 730, "category": "Advertising", "vendor": "Facebook"},

    # Hotjar
    {"name": "_hjid", "domain": ".hotjar.com", "duration_days": 365, "category": "Analytics", "vendor": "Hotjar"},
    {"name": "_hjSessionUser_*", "domain": ".hotjar.com", "duration_days": 365, "category": "Analytics", "vendor": "Hotjar"},
    {"name": "_hjSession_*", "domain": ".hotjar.com", "duration_days": 0, "category": "Analytics", "vendor": "Hotjar"},

    # Mixpanel
    {"name": "mp_*_mixpanel", "domain": ".mixpanel.com", "duration_days": 365, "category": "Analytics", "vendor": "Mixpanel"},

    # Session cookies (Necessary)
    {"name": "PHPSESSID", "domain": ".example.com", "duration_days": 0, "category": "Necessary", "vendor": "Generic"},
    {"name": "JSESSIONID", "domain": ".example.com", "duration_days": 0, "category": "Necessary", "vendor": "Generic"},
    {"name": "sessionid", "domain": ".example.com", "duration_days": 0, "category": "Necessary", "vendor": "Generic"},
    {"name": "session", "domain": ".example.com", "duration_days": 0, "category": "Necessary", "vendor": "Generic"},

    # CSRF/Auth (Necessary)
    {"name": "csrf_token", "domain": ".example.com", "duration_days": 0, "category": "Necessary", "vendor": "Generic"},
    {"name": "csrftoken", "domain": ".example.com", "duration_days": 0, "category": "Necessary", "vendor": "Generic"},
    {"name": "XSRF-TOKEN", "domain": ".example.com", "duration_days": 0, "category": "Necessary", "vendor": "Generic"},
    {"name": "auth_token", "domain": ".example.com", "duration_days": 7, "category": "Necessary", "vendor": "Generic"},

    # Functional cookies
    {"name": "language", "domain": ".example.com", "duration_days": 365, "category": "Functional", "vendor": "Generic"},
    {"name": "lang", "domain": ".example.com", "duration_days": 365, "category": "Functional", "vendor": "Generic"},
    {"name": "currency", "domain": ".example.com", "duration_days": 30, "category": "Functional", "vendor": "Generic"},
    {"name": "theme", "domain": ".example.com", "duration_days": 365, "category": "Functional", "vendor": "Generic"},
    {"name": "timezone", "domain": ".example.com", "duration_days": 365, "category": "Functional", "vendor": "Generic"},

    # Google Ads
    {"name": "IDE", "domain": ".doubleclick.net", "duration_days": 390, "category": "Advertising", "vendor": "Google"},
    {"name": "test_cookie", "domain": ".doubleclick.net", "duration_days": 0, "category": "Advertising", "vendor": "Google"},
    {"name": "_gcl_au", "domain": ".google.com", "duration_days": 90, "category": "Advertising", "vendor": "Google"},

    # LinkedIn
    {"name": "bcookie", "domain": ".linkedin.com", "duration_days": 730, "category": "Advertising", "vendor": "LinkedIn"},
    {"name": "lidc", "domain": ".linkedin.com", "duration_days": 1, "category": "Advertising", "vendor": "LinkedIn"},
    {"name": "li_sugr", "domain": ".linkedin.com", "duration_days": 90, "category": "Advertising", "vendor": "LinkedIn"},

    # Microsoft Clarity
    {"name": "_clck", "domain": ".clarity.ms", "duration_days": 365, "category": "Analytics", "vendor": "Microsoft"},
    {"name": "_clsk", "domain": ".clarity.ms", "duration_days": 1, "category": "Analytics", "vendor": "Microsoft"},
    {"name": "CLID", "domain": ".clarity.ms", "duration_days": 365, "category": "Analytics", "vendor": "Microsoft"},

    # Cloudflare (Necessary)
    {"name": "__cf_bm", "domain": ".cloudflare.com", "duration_days": 0, "category": "Necessary", "vendor": "Cloudflare"},
    {"name": "_cfuvid", "domain": ".cloudflare.com", "duration_days": 0, "category": "Necessary", "vendor": "Cloudflare"},

    # Consent cookies (Functional)
    {"name": "cookie_consent", "domain": ".example.com", "duration_days": 365, "category": "Functional", "vendor": "Generic"},
    {"name": "cookieconsent_status", "domain": ".example.com", "duration_days": 365, "category": "Functional", "vendor": "Generic"},
]


def load_cookie_rules() -> List[Dict[str, Any]]:
    """Load cookie rules from cookie_rules.json."""
    try:
        with open(COOKIE_RULES_FILE, "r") as f:
            data = json.load(f)
            return data.get("rules", [])
    except FileNotFoundError:
        print(f"Warning: {COOKIE_RULES_FILE} not found")
        return []


def generate_cookies_from_pattern(pattern: str, category: str, count: int = 10) -> List[Dict[str, Any]]:
    """
    Generate synthetic cookies from regex pattern.

    Args:
        pattern: Regex pattern (e.g., "_ga(_.*)?")
        category: Cookie category
        count: Number of variations to generate

    Returns:
        List of synthetic cookie dictionaries
    """
    cookies = []

    # Extract base name from pattern
    base_names = extract_base_names_from_pattern(pattern)

    for base_name in base_names[:count]:
        # Determine typical properties based on category
        if category == "Necessary":
            duration_days = random.choice([0, 0, 0, 1, 7])  # Mostly session
            is_third_party = False
            httpOnly = True
            secure = True
            sameSite = "Strict"
        elif category == "Functional":
            duration_days = random.choice([30, 90, 365])
            is_third_party = False
            httpOnly = False
            secure = True
            sameSite = "Lax"
        elif category == "Analytics":
            duration_days = random.choice([1, 30, 90, 365, 730])
            is_third_party = True
            httpOnly = False
            secure = True
            sameSite = "None"
        else:  # Advertising
            duration_days = random.choice([90, 180, 365, 390])
            is_third_party = True
            httpOnly = False
            secure = True
            sameSite = "None"

        # Generate domain based on third-party status
        if is_third_party:
            domain = f".{get_vendor_domain(base_name)}"
        else:
            domain = ".example.com"

        cookie = {
            "name": base_name,
            "domain": domain,
            "path": "/",
            "duration_days": duration_days,
            "is_session": duration_days == 0,
            "httpOnly": httpOnly,
            "secure": secure,
            "sameSite": sameSite,
            "cookie_type": "Third Party" if is_third_party else "First Party",
            "size": random.randint(20, 100),
            "set_after_accept": category != "Necessary",
            "category": category,
            "source": "cookie_rules.json",
        }

        cookies.append(cookie)

    return cookies


def extract_base_names_from_pattern(pattern: str) -> List[str]:
    """Extract concrete cookie names from regex pattern."""
    # Split by | for multiple patterns
    parts = pattern.split("|")
    names = []

    for part in parts:
        # Remove regex special chars to get base name
        clean = re.sub(r"[\(\)\?\*\.\^\$\[\]]", "", part)
        if clean and len(clean) > 1:
            names.append(clean)

    return names[:5]  # Limit to 5 variations per pattern


def get_vendor_domain(cookie_name: str) -> str:
    """Infer vendor domain from cookie name."""
    name_lower = cookie_name.lower()

    if "_ga" in name_lower or "_gid" in name_lower or "_gat" in name_lower:
        return "google-analytics.com"
    elif "_fb" in name_lower or "datr" in name_lower:
        return "facebook.com"
    elif "_hj" in name_lower:
        return "hotjar.com"
    elif "mp_" in name_lower or "mixpanel" in name_lower:
        return "mixpanel.com"
    elif "clid" in name_lower or "_clck" in name_lower:
        return "clarity.ms"
    elif "ide" in name_lower or "test_cookie" in name_lower:
        return "doubleclick.net"
    elif "bcookie" in name_lower or "lidc" in name_lower:
        return "linkedin.com"
    elif "__cf" in name_lower:
        return "cloudflare.com"
    else:
        return "unknown-tracking.com"


def create_csv_row(cookie: Dict[str, Any]) -> Dict[str, Any]:
    """Convert cookie dict to CSV row format."""
    duration_str = "Session" if cookie.get("is_session", False) else f"{cookie['duration_days']} days"

    return {
        "cookie_name": cookie["name"],
        "domain": cookie["domain"],
        "path": cookie.get("path", "/"),
        "duration_days": cookie.get("duration_days", 0),
        "duration_str": duration_str,
        "is_session": cookie.get("is_session", False),
        "httpOnly": cookie.get("httpOnly", False),
        "secure": cookie.get("secure", True),
        "sameSite": cookie.get("sameSite", "None"),
        "cookie_type": cookie.get("cookie_type", "First Party"),
        "size": cookie.get("size", 50),
        "set_after_accept": cookie.get("set_after_accept", False),
        "category": cookie["category"],
        "confidence": 1.0,  # High confidence for known cookies
        "source": cookie.get("source", "Manual"),
    }


def main():
    """Main bootstrap script."""
    print("=" * 60)
    print("BOOTSTRAP TRAINING DATA")
    print("=" * 60)

    all_cookies = []

    # 1. Load from cookie_rules.json
    print("\n1. Loading cookie rules...")
    rules = load_cookie_rules()
    print(f"   Found {len(rules)} rules")

    for rule in rules:
        pattern = rule["pattern"]
        category_raw = rule["category"]
        category = CATEGORY_MAP.get(category_raw)

        if category is None:
            continue  # Skip unknown categories

        # Generate synthetic cookies from pattern
        synthetic_cookies = generate_cookies_from_pattern(pattern, category, count=5)
        all_cookies.extend(synthetic_cookies)

    print(f"   Generated {len(all_cookies)} synthetic cookies from rules")

    # 2. Add known cookies
    print("\n2. Adding known cookie datasets...")
    for known_cookie in KNOWN_COOKIES:
        all_cookies.append(known_cookie)

    print(f"   Added {len(KNOWN_COOKIES)} known cookies")

    # 3. Generate additional variations
    print("\n3. Generating additional variations...")
    additional = generate_additional_variations()
    all_cookies.extend(additional)
    print(f"   Generated {len(additional)} additional variations")

    # 4. Deduplicate by (name, domain)
    print("\n4. Deduplicating...")
    unique_cookies = {}
    for cookie in all_cookies:
        key = (cookie["name"], cookie["domain"])
        if key not in unique_cookies:
            unique_cookies[key] = cookie

    all_cookies = list(unique_cookies.values())
    print(f"   {len(all_cookies)} unique cookies after deduplication")

    # 5. Category distribution
    print("\n5. Category distribution:")
    category_counts = {}
    for cookie in all_cookies:
        cat = cookie["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    for cat, count in sorted(category_counts.items()):
        percentage = (count / len(all_cookies)) * 100
        print(f"   {cat:15s}: {count:4d} ({percentage:5.1f}%)")

    # 6. Write to CSV
    print(f"\n6. Writing to {OUTPUT_FILE}...")
    OUTPUT_FILE.parent.mkdir(exist_ok=True)

    fieldnames = [
        "cookie_name", "domain", "path", "duration_days", "duration_str",
        "is_session", "httpOnly", "secure", "sameSite", "cookie_type",
        "size", "set_after_accept", "category", "confidence", "source"
    ]

    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for cookie in all_cookies:
            row = create_csv_row(cookie)
            writer.writerow(row)

    print(f"   ✓ Wrote {len(all_cookies)} labeled cookies to CSV")

    # 7. Summary
    print("\n" + "=" * 60)
    print("BOOTSTRAP COMPLETE")
    print("=" * 60)
    print(f"Total training samples: {len(all_cookies)}")
    print(f"Output file: {OUTPUT_FILE}")
    print("\nNext steps:")
    print("  1. Review the generated CSV file")
    print("  2. Run: python scripts/train_model.py")
    print("  3. Test with: python scripts/test_classifier.py")
    print("=" * 60)


def generate_additional_variations() -> List[Dict[str, Any]]:
    """Generate additional synthetic cookie variations."""
    variations = []

    # Generate more session cookies (Necessary)
    session_prefixes = ["sid", "sess", "auth", "token", "user", "login", "csrf"]
    for prefix in session_prefixes:
        for suffix in ["", "_id", "_token", "id"]:
            variations.append({
                "name": f"{prefix}{suffix}",
                "domain": ".example.com",
                "duration_days": 0,
                "is_session": True,
                "httpOnly": True,
                "secure": True,
                "sameSite": "Strict",
                "cookie_type": "First Party",
                "size": random.randint(30, 80),
                "set_after_accept": False,
                "category": "Necessary",
                "source": "Synthetic",
            })

    # Generate functional cookies
    functional_names = [
        ("language", 365), ("locale", 365), ("currency", 90),
        ("theme", 365), ("timezone", 365), ("preferences", 180),
        ("font_size", 365), ("layout", 365),
    ]
    for name, duration in functional_names:
        variations.append({
            "name": name,
            "domain": ".example.com",
            "duration_days": duration,
            "httpOnly": False,
            "secure": True,
            "sameSite": "Lax",
            "cookie_type": "First Party",
            "size": random.randint(10, 40),
            "set_after_accept": True,
            "category": "Functional",
            "source": "Synthetic",
        })

    # Generate tracking IDs (Analytics)
    tracking_patterns = [
        ("uid", ".tracker.com", 365),
        ("visitor_id", ".analytics-service.com", 730),
        ("tracking_id", ".stats-service.com", 365),
        ("analytics_session", ".analytics.io", 0),
    ]
    for name, domain, duration in tracking_patterns:
        variations.append({
            "name": name,
            "domain": domain,
            "duration_days": duration,
            "httpOnly": False,
            "secure": True,
            "sameSite": "None",
            "cookie_type": "Third Party",
            "size": random.randint(40, 100),
            "set_after_accept": True,
            "category": "Analytics",
            "source": "Synthetic",
        })

    # Generate ad cookies (Advertising)
    ad_patterns = [
        ("ad_id", ".adnetwork.com", 90),
        ("conversion", ".advertising.com", 90),
        ("retargeting", ".retarget.io", 180),
        ("audience", ".dsp-platform.com", 365),
    ]
    for name, domain, duration in ad_patterns:
        variations.append({
            "name": name,
            "domain": domain,
            "duration_days": duration,
            "httpOnly": False,
            "secure": True,
            "sameSite": "None",
            "cookie_type": "Third Party",
            "size": random.randint(50, 120),
            "set_after_accept": True,
            "category": "Advertising",
            "source": "Synthetic",
        })

    return variations


if __name__ == "__main__":
    main()
