#!/usr/bin/env python3
"""
Manual Cookie Labeling Tool

Interactive CLI tool for manually labeling cookies collected from websites.
Displays cookie properties and allows quick category assignment.

Usage:
    python scripts/label_cookies.py [--input FILE] [--output FILE]

Controls:
    N - Necessary
    F - Functional
    A - Analytics
    D - Advertising (aDs)
    S - Skip
    Q - Quit (saves progress)
    ? - Show help
"""

import csv
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))


CATEGORIES = {
    "n": "Necessary",
    "f": "Functional",
    "a": "Analytics",
    "d": "Advertising",  # D for aDs
}


def load_cookies(input_file: Path) -> List[Dict[str, Any]]:
    """Load cookies from CSV file."""
    if not input_file.exists():
        print(f"✗ Input file not found: {input_file}")
        sys.exit(1)

    cookies = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cookies.append(dict(row))

    return cookies


def save_cookies(cookies: List[Dict[str, Any]], output_file: Path):
    """Save cookies to CSV file."""
    if not cookies:
        return

    output_file.parent.mkdir(exist_ok=True)

    # Get all fieldnames from first cookie
    fieldnames = list(cookies[0].keys())

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cookies)


def display_cookie(cookie: Dict[str, Any], index: int, total: int):
    """Display cookie information."""
    print("\n" + "=" * 70)
    print(f"Cookie {index + 1}/{total}")
    print("=" * 70)

    # Cookie name and domain
    name = cookie.get("name") or cookie.get("cookie_name", "Unknown")
    domain = cookie.get("domain", "Unknown")
    print(f"\nName:   {name}")
    print(f"Domain: {domain}")

    # Cookie type and duration
    cookie_type = cookie.get("cookie_type", "Unknown")
    duration = cookie.get("cookie_duration") or cookie.get("duration_str", "Unknown")
    is_session = cookie.get("is_session", "").lower() in ("true", "1", "yes")

    print(f"\nType:     {cookie_type}")
    print(f"Duration: {duration} {'(Session)' if is_session else ''}")

    # Security flags
    http_only = cookie.get("httpOnly", "").lower() in ("true", "1", "yes")
    secure = cookie.get("secure", "").lower() in ("true", "1", "yes")
    same_site = cookie.get("sameSite", "Unknown")

    print(f"\nSecurity:")
    print(f"  HttpOnly:  {http_only}")
    print(f"  Secure:    {secure}")
    print(f"  SameSite:  {same_site}")

    # Source URL (if available)
    source_url = cookie.get("source_url", "")
    if source_url:
        print(f"\nSource: {source_url}")

    # Current category (if labeled)
    current_category = cookie.get("category", "")
    if current_category:
        print(f"\nCurrent Label: {current_category}")


def get_category_from_user() -> Optional[str]:
    """Get category selection from user."""
    print("\n" + "-" * 70)
    print("Select category:")
    print("  [N] Necessary   - Essential for site functionality")
    print("  [F] Functional  - User preferences and settings")
    print("  [A] Analytics   - Usage tracking and statistics")
    print("  [D] Advertising - Ads and marketing")
    print("  [S] Skip        - Skip this cookie")
    print("  [Q] Quit        - Save progress and exit")
    print("  [?] Help        - Show examples")
    print("-" * 70)

    while True:
        choice = input("\nYour choice: ").strip().lower()

        if choice in CATEGORIES:
            return CATEGORIES[choice]
        elif choice == "s":
            return None  # Skip
        elif choice == "q":
            return "QUIT"
        elif choice == "?":
            show_help()
        else:
            print("Invalid choice. Please enter N, F, A, D, S, Q, or ?")


def show_help():
    """Show category examples."""
    print("\n" + "=" * 70)
    print("CATEGORY EXAMPLES")
    print("=" * 70)

    print("\nNECESSARY - Essential for site to function:")
    print("  • Session IDs: PHPSESSID, JSESSIONID, sessionid")
    print("  • CSRF tokens: csrf_token, XSRF-TOKEN")
    print("  • Authentication: auth_token, login_token")
    print("  • Load balancing: awsalb, server_id")

    print("\nFUNCTIONAL - User preferences:")
    print("  • Language/locale: language, lang, locale")
    print("  • Theme: theme, dark_mode")
    print("  • Currency: currency")
    print("  • View settings: view_mode, sidebar_state")

    print("\nANALYTICS - Usage tracking:")
    print("  • Google Analytics: _ga, _gid, _gat")
    print("  • Hotjar: _hjid, _hjSession")
    print("  • Microsoft Clarity: _clck, _clsk")
    print("  • Any cookie measuring performance/usage")

    print("\nADVERTISING - Ads and marketing:")
    print("  • Google Ads: IDE, test_cookie, _gcl_*")
    print("  • Facebook: _fbp, _fbc, fr")
    print("  • LinkedIn: bcookie, lidc")
    print("  • Any cookie for ad targeting/personalization")

    print("\n" + "=" * 70)


def label_cookies_interactive(cookies: List[Dict[str, Any]]) -> int:
    """
    Interactively label cookies.

    Returns:
        Number of cookies labeled
    """
    labeled_count = 0
    already_labeled_count = 0

    for i, cookie in enumerate(cookies):
        # Skip if already labeled
        current_category = cookie.get("category", "")
        if current_category and current_category in ["Necessary", "Functional", "Analytics", "Advertising"]:
            already_labeled_count += 1
            continue

        # Display cookie
        display_cookie(cookie, i, len(cookies))

        # Get category
        category = get_category_from_user()

        if category == "QUIT":
            print(f"\nQuitting... (labeled {labeled_count} cookies)")
            break
        elif category is None:
            # Skip
            continue
        else:
            # Label cookie
            cookie["category"] = category
            cookie["confidence"] = "1.0"  # Manual labels are high confidence
            cookie["source"] = cookie.get("source", "ManualLabel")
            labeled_count += 1
            print(f"✓ Labeled as: {category}")

    return labeled_count, already_labeled_count


def print_statistics(cookies: List[Dict[str, Any]]):
    """Print statistics about labeled cookies."""
    print("\n" + "=" * 70)
    print("LABELING STATISTICS")
    print("=" * 70)

    # Count labeled vs unlabeled
    labeled = [c for c in cookies if c.get("category") in ["Necessary", "Functional", "Analytics", "Advertising"]]
    unlabeled = len(cookies) - len(labeled)

    print(f"\nTotal cookies:    {len(cookies)}")
    print(f"Labeled:          {len(labeled)} ({len(labeled)/len(cookies)*100:.1f}%)")
    print(f"Unlabeled:        {unlabeled} ({unlabeled/len(cookies)*100:.1f}%)")

    if labeled:
        # By category
        category_counts = Counter(c["category"] for c in labeled)
        print(f"\nLabeled by category:")
        for category, count in sorted(category_counts.items()):
            percentage = (count / len(labeled)) * 100
            print(f"  {category:15s}: {count:4d} ({percentage:5.1f}%)")

    print("=" * 70)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Interactive cookie labeling tool"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default="training_data/collected_cookies.csv",
        help="Input CSV file with unlabeled cookies"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output CSV file (defaults to same as input)"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path

    print("=" * 70)
    print("MANUAL COOKIE LABELING TOOL")
    print("=" * 70)
    print(f"\nInput:  {input_path}")
    print(f"Output: {output_path}")

    # Load cookies
    print(f"\nLoading cookies from {input_path}...")
    cookies = load_cookies(input_path)
    print(f"✓ Loaded {len(cookies)} cookies")

    # Show initial statistics
    print_statistics(cookies)

    # Start labeling
    print("\n" + "=" * 70)
    print("STARTING INTERACTIVE LABELING")
    print("=" * 70)
    print("\nPress Ctrl+C to quit and save progress")
    print("Type ? at any prompt to see examples")

    try:
        labeled_count, already_labeled = label_cookies_interactive(cookies)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Saving progress...")
        labeled_count = 0
        already_labeled = 0

    # Save cookies
    print(f"\nSaving to {output_path}...")
    save_cookies(cookies, output_path)
    print("✓ Saved")

    # Show final statistics
    print_statistics(cookies)

    print("\n" + "=" * 70)
    print("SESSION SUMMARY")
    print("=" * 70)
    print(f"Newly labeled:     {labeled_count}")
    print(f"Already labeled:   {already_labeled}")
    print(f"Saved to:          {output_path}")
    print("=" * 70)

    # Next steps
    unlabeled_remaining = len([c for c in cookies if not c.get("category") or c["category"] not in ["Necessary", "Functional", "Analytics", "Advertising"]])

    if unlabeled_remaining > 0:
        print(f"\n⚠ {unlabeled_remaining} cookies still need labeling")
        print(f"Run again to continue: python scripts/label_cookies.py --input {input_path}")
    else:
        print("\n✓ All cookies labeled!")
        print(f"\nNext steps:")
        print(f"1. Merge with other training data:")
        print(f"   python scripts/merge_training_data.py")
        print(f"2. Retrain model:")
        print(f"   python scripts/train_model.py")

    print()


if __name__ == "__main__":
    main()
