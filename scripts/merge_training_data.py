#!/usr/bin/env python3
"""
Merge Training Data from Multiple Sources

Combines cookie data from multiple sources with deduplication and validation:
- Bootstrap labeled data (rules-based)
- Public dataset imports (CookiePedia, IAB GVL)
- Website scraping data (manual labels)
- Admin feedback corrections

Usage:
    python scripts/merge_training_data.py [--output FILE] [--balance]
"""

import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
from collections import Counter, defaultdict
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


# Valid categories
VALID_CATEGORIES = {"Necessary", "Functional", "Analytics", "Advertising"}

# Source priority for deduplication (higher = wins)
SOURCE_PRIORITY = {
    "AdminFeedback": 5,  # Highest - human corrections
    "DB": 4,  # Database overrides
    "PublicDB": 3,  # Known cookie databases
    "Bootstrap": 2,  # Rules-based bootstrap
    "WebScrape": 1,  # Lowest - needs validation
}


def load_csv_data(file_path: Path) -> List[Dict[str, Any]]:
    """Load data from CSV file."""
    if not file_path.exists():
        return []

    cookies = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cookies.append(dict(row))

    return cookies


def normalize_cookie(cookie: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize cookie data to consistent format."""
    # Handle field name variations
    name = cookie.get("cookie_name") or cookie.get("name", "")
    domain = cookie.get("domain", "")

    # Ensure domain starts with dot for consistency
    if domain and not domain.startswith("."):
        domain = f".{domain}"

    # Parse duration
    duration_days = cookie.get("duration_days", "")
    if duration_days == "" or duration_days is None:
        duration_days = 0.0
    else:
        try:
            duration_days = float(duration_days)
        except (ValueError, TypeError):
            duration_days = 0.0

    # Parse boolean fields
    def parse_bool(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)

    is_session = parse_bool(cookie.get("is_session", duration_days == 0))
    http_only = parse_bool(cookie.get("httpOnly", False))
    secure = parse_bool(cookie.get("secure", False))
    set_after_accept = parse_bool(cookie.get("set_after_accept", False))

    # Cookie type
    cookie_type = cookie.get("cookie_type", "First Party")
    if cookie_type not in ["First Party", "Third Party"]:
        cookie_type = "First Party"

    # SameSite
    same_site = cookie.get("sameSite", "Lax")
    if same_site not in ["Strict", "Lax", "None"]:
        same_site = "Lax"

    # Category
    category = cookie.get("category", "")
    if category not in VALID_CATEGORIES:
        category = ""  # Mark as unlabeled

    # Confidence
    confidence = cookie.get("confidence", "")
    if confidence == "" or confidence is None:
        confidence = 1.0 if category else 0.0
    else:
        try:
            confidence = float(confidence)
        except (ValueError, TypeError):
            confidence = 0.0

    # Size
    size = cookie.get("size", 50)
    try:
        size = int(size)
    except (ValueError, TypeError):
        size = 50

    return {
        "cookie_name": name,
        "domain": domain,
        "path": cookie.get("path", "/"),
        "duration_days": duration_days,
        "is_session": is_session,
        "httpOnly": http_only,
        "secure": secure,
        "sameSite": same_site,
        "cookie_type": cookie_type,
        "size": size,
        "set_after_accept": set_after_accept,
        "category": category,
        "confidence": confidence,
        "source": cookie.get("source", "Unknown"),
    }


def get_cookie_key(cookie: Dict[str, Any]) -> Tuple[str, str]:
    """Get unique key for cookie (name, domain)."""
    name = cookie.get("cookie_name", "").lower()
    domain = cookie.get("domain", "").lower()
    return (name, domain)


def deduplicate_cookies(cookies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate cookies by (name, domain) key.
    Priority: AdminFeedback > DB > PublicDB > Bootstrap > WebScrape
    """
    cookie_map: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for cookie in cookies:
        key = get_cookie_key(cookie)
        source = cookie.get("source", "Unknown")

        # Extract base source (remove suffixes like _Google, _Facebook)
        base_source = source.split("_")[0] if "_" in source else source
        priority = SOURCE_PRIORITY.get(base_source, 0)

        # Check if we should keep this cookie
        if key not in cookie_map:
            # First occurrence
            cookie_map[key] = cookie
        else:
            # Duplicate - compare priorities
            existing = cookie_map[key]
            existing_source = existing.get("source", "Unknown").split("_")[0]
            existing_priority = SOURCE_PRIORITY.get(existing_source, 0)

            if priority > existing_priority:
                # Higher priority - replace
                cookie_map[key] = cookie
            elif priority == existing_priority:
                # Same priority - prefer higher confidence
                if cookie.get("confidence", 0) > existing.get("confidence", 0):
                    cookie_map[key] = cookie

    return list(cookie_map.values())


def validate_cookies(cookies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate and clean cookie data."""
    valid_cookies = []

    for cookie in cookies:
        # Skip if missing required fields
        if not cookie.get("cookie_name") or not cookie.get("domain"):
            continue

        # Skip test cookies
        name_lower = cookie["cookie_name"].lower()
        if "test" in name_lower and name_lower.startswith("_test"):
            continue

        # Skip if no category (unlabeled)
        if not cookie.get("category") or cookie["category"] not in VALID_CATEGORIES:
            continue

        # Skip if invalid category
        if cookie["category"] not in VALID_CATEGORIES:
            continue

        valid_cookies.append(cookie)

    return valid_cookies


def balance_dataset(cookies: List[Dict[str, Any]], target_per_category: int = None) -> List[Dict[str, Any]]:
    """
    Balance dataset across categories using undersampling.

    Args:
        cookies: List of cookies
        target_per_category: Target samples per category (None = use min count)
    """
    # Group by category
    by_category = defaultdict(list)
    for cookie in cookies:
        category = cookie.get("category")
        if category:
            by_category[category].append(cookie)

    # Find target count
    if target_per_category is None:
        counts = [len(cookies) for cookies in by_category.values()]
        if not counts:
            return []
        target_per_category = min(counts)

    print(f"\nBalancing dataset to {target_per_category} samples per category...")

    # Sample from each category
    balanced = []
    for category, category_cookies in by_category.items():
        if len(category_cookies) <= target_per_category:
            # Keep all
            balanced.extend(category_cookies)
            print(f"  {category:15s}: {len(category_cookies):4d} (kept all)")
        else:
            # Undersample
            import random
            sampled = random.sample(category_cookies, target_per_category)
            balanced.extend(sampled)
            print(f"  {category:15s}: {len(category_cookies):4d} → {target_per_category} (sampled)")

    return balanced


def print_statistics(cookies: List[Dict[str, Any]], title: str = "Dataset Statistics"):
    """Print statistics about cookie dataset."""
    if not cookies:
        print(f"\n{title}: No cookies!")
        return

    print(f"\n{'=' * 70}")
    print(title)
    print(f"{'=' * 70}")

    print(f"\nTotal cookies: {len(cookies)}")

    # By category
    category_counts = Counter(c.get("category", "Unknown") for c in cookies)
    print(f"\nBy category:")
    for category, count in sorted(category_counts.items()):
        percentage = (count / len(cookies)) * 100
        print(f"  {category:15s}: {count:4d} ({percentage:5.1f}%)")

    # By source
    source_counts = Counter(c.get("source", "Unknown") for c in cookies)
    print(f"\nBy source:")
    for source, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        percentage = (count / len(cookies)) * 100
        print(f"  {source:20s}: {count:4d} ({percentage:5.1f}%)")

    # By cookie type
    type_counts = Counter(c.get("cookie_type", "Unknown") for c in cookies)
    print(f"\nBy cookie type:")
    for cookie_type, count in type_counts.items():
        percentage = (count / len(cookies)) * 100
        print(f"  {cookie_type:15s}: {count:4d} ({percentage:5.1f}%)")

    # Average confidence
    confidences = [c.get("confidence", 0) for c in cookies if c.get("confidence")]
    if confidences:
        avg_confidence = sum(confidences) / len(confidences)
        print(f"\nAverage confidence: {avg_confidence:.1%}")

    print(f"{'=' * 70}")


def save_to_csv(cookies: List[Dict[str, Any]], output_file: Path):
    """Save merged cookies to CSV file."""
    if not cookies:
        print("No cookies to save!")
        return

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


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Merge training data from multiple sources"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="training_data/merged_training_data.csv",
        help="Output CSV file path"
    )
    parser.add_argument(
        "--balance",
        action="store_true",
        help="Balance dataset across categories"
    )
    parser.add_argument(
        "--balance-count",
        type=int,
        default=None,
        help="Target samples per category for balancing"
    )

    args = parser.parse_args()

    print(f"\n{'=' * 70}")
    print("MERGING TRAINING DATA FROM MULTIPLE SOURCES")
    print(f"{'=' * 70}\n")

    # Define source files
    base_dir = Path(__file__).parent.parent
    sources = [
        ("Bootstrap", base_dir / "training_data" / "labeled_cookies.csv"),
        ("Public Dataset", base_dir / "training_data" / "public_dataset_cookies.csv"),
        ("Enhanced Bootstrap", base_dir / "training_data" / "enhanced_bootstrap_cookies.csv"),
        ("Xfinity Manual", base_dir / "training_data" / "xfinity_manual_cookies.csv"),
        ("Web Scraping", base_dir / "training_data" / "collected_cookies.csv"),
        ("Admin Feedback", base_dir / "training_data" / "admin_feedback.csv"),
    ]

    # Load data from all sources
    all_cookies = []
    loaded_sources = []

    for source_name, file_path in sources:
        print(f"Loading from {source_name}...")
        cookies = load_csv_data(file_path)

        if cookies:
            print(f"  ✓ Loaded {len(cookies)} cookies from {file_path.name}")
            all_cookies.extend(cookies)
            loaded_sources.append(source_name)
        else:
            print(f"  ⚠ No data found in {file_path.name}")

    if not all_cookies:
        print("\n✗ No data to merge!")
        return

    print(f"\n{'=' * 70}")
    print(f"Total cookies loaded: {len(all_cookies)}")
    print(f"{'=' * 70}")

    # Step 1: Normalize
    print(f"\nStep 1: Normalizing cookies...")
    normalized = [normalize_cookie(c) for c in all_cookies]
    print(f"  ✓ Normalized {len(normalized)} cookies")

    # Step 2: Deduplicate
    print(f"\nStep 2: Deduplicating cookies...")
    before_dedup = len(normalized)
    deduplicated = deduplicate_cookies(normalized)
    removed = before_dedup - len(deduplicated)
    print(f"  ✓ Removed {removed} duplicates ({len(deduplicated)} unique cookies)")

    # Step 3: Validate
    print(f"\nStep 3: Validating cookies...")
    before_validation = len(deduplicated)
    validated = validate_cookies(deduplicated)
    removed = before_validation - len(validated)
    print(f"  ✓ Removed {removed} invalid cookies ({len(validated)} valid cookies)")

    # Print statistics before balancing
    print_statistics(validated, "BEFORE BALANCING")

    # Step 4: Balance (optional)
    final_cookies = validated
    if args.balance:
        print(f"\nStep 4: Balancing dataset...")
        final_cookies = balance_dataset(validated, args.balance_count)
        print_statistics(final_cookies, "AFTER BALANCING")
    else:
        print(f"\nStep 4: Skipping balancing (use --balance to enable)")

    # Save to CSV
    output_path = Path(args.output)
    save_to_csv(final_cookies, output_path)

    # Print summary
    print(f"\n{'=' * 70}")
    print("MERGE COMPLETE")
    print(f"{'=' * 70}")
    print(f"\nSources merged: {', '.join(loaded_sources)}")
    print(f"Final dataset: {len(final_cookies)} labeled cookies")
    print(f"Output file: {output_path}")

    print(f"\n{'=' * 70}")
    print("NEXT STEPS")
    print(f"{'=' * 70}")
    print(f"1. Review merged data: {output_path}")
    print(f"2. Retrain model with more data:")
    print(f"   python scripts/train_model.py --input {output_path}")
    print(f"3. Test new model:")
    print(f"   python scripts/test_classifier.py")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
