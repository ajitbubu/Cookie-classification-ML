#!/usr/bin/env python3
"""
Test Script for Cookie Classifier

Tests the trained ML classifier with example cookies and generates reports.

Usage:
    python scripts/test_classifier.py [--interactive]

Options:
    --interactive    Enter cookies manually for testing
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ml_classifier.classifier import MLCookieClassifier, ClassificationResult


# Test cookie samples
TEST_COOKIES = [
    {
        "name": "_ga",
        "domain": ".google-analytics.com",
        "cookie_duration": "730 days",
        "cookie_type": "Third Party",
        "httpOnly": False,
        "secure": True,
        "sameSite": "None",
        "size": 50,
        "set_after_accept": True,
        "expected_category": "Analytics",
    },
    {
        "name": "_gid",
        "domain": ".google-analytics.com",
        "cookie_duration": "1 days",
        "cookie_type": "Third Party",
        "httpOnly": False,
        "secure": True,
        "sameSite": "None",
        "expected_category": "Analytics",
    },
    {
        "name": "_fbp",
        "domain": ".facebook.com",
        "cookie_duration": "90 days",
        "cookie_type": "Third Party",
        "httpOnly": False,
        "secure": True,
        "sameSite": "None",
        "set_after_accept": True,
        "expected_category": "Advertising",
    },
    {
        "name": "IDE",
        "domain": ".doubleclick.net",
        "cookie_duration": "390 days",
        "cookie_type": "Third Party",
        "httpOnly": False,
        "secure": True,
        "sameSite": "None",
        "expected_category": "Advertising",
    },
    {
        "name": "sessionid",
        "domain": ".example.com",
        "cookie_duration": "Session",
        "cookie_type": "First Party",
        "httpOnly": True,
        "secure": True,
        "sameSite": "Strict",
        "set_after_accept": False,
        "expected_category": "Necessary",
    },
    {
        "name": "csrf_token",
        "domain": ".example.com",
        "cookie_duration": "Session",
        "cookie_type": "First Party",
        "httpOnly": True,
        "secure": True,
        "sameSite": "Strict",
        "set_after_accept": False,
        "expected_category": "Necessary",
    },
    {
        "name": "language",
        "domain": ".example.com",
        "cookie_duration": "365 days",
        "cookie_type": "First Party",
        "httpOnly": False,
        "secure": True,
        "sameSite": "Lax",
        "expected_category": "Functional",
    },
    {
        "name": "theme",
        "domain": ".example.com",
        "cookie_duration": "365 days",
        "cookie_type": "First Party",
        "httpOnly": False,
        "secure": True,
        "sameSite": "Lax",
        "expected_category": "Functional",
    },
    {
        "name": "_hjid",
        "domain": ".hotjar.com",
        "cookie_duration": "365 days",
        "cookie_type": "Third Party",
        "httpOnly": False,
        "secure": True,
        "sameSite": "None",
        "set_after_accept": True,
        "expected_category": "Analytics",
    },
    {
        "name": "bcookie",
        "domain": ".linkedin.com",
        "cookie_duration": "730 days",
        "cookie_type": "Third Party",
        "httpOnly": False,
        "secure": True,
        "sameSite": "None",
        "set_after_accept": True,
        "expected_category": "Advertising",
    },
]


def print_classification_result(
    cookie: dict, result: ClassificationResult, expected: str = None
):
    """Print formatted classification result."""
    print(f"\n{'=' * 70}")
    print(f"Cookie: {cookie['name']}")
    print(f"Domain: {cookie['domain']}")
    print(f"Duration: {cookie.get('cookie_duration', 'N/A')}")
    print(f"-" * 70)
    print(f"Predicted Category: {result.category}")
    print(f"Confidence: {result.confidence:.1%}")

    if expected:
        match = "✓" if result.category == expected else "✗"
        print(f"Expected Category: {expected} {match}")

    print(f"\nProbability Distribution:")
    for category, prob in sorted(
        result.probabilities.items(), key=lambda x: x[1], reverse=True
    ):
        bar = "█" * int(prob * 40)
        print(f"  {category:15s} {prob:6.1%} {bar}")

    print(f"\nEvidence:")
    for evidence in result.evidence:
        print(f"  • {evidence}")

    if result.requires_review:
        print(f"\n⚠ Manual review recommended (low confidence)")

    print(f"=" * 70)


def run_batch_test(classifier: MLCookieClassifier):
    """Run batch test on predefined test cookies."""
    print("\n" + "=" * 70)
    print("BATCH CLASSIFICATION TEST")
    print("=" * 70)
    print(f"Testing {len(TEST_COOKIES)} cookies...")

    # Batch classify
    results = classifier.classify_batch(TEST_COOKIES)

    # Track accuracy
    correct = 0
    total = 0
    low_confidence_count = 0

    for cookie, result in zip(TEST_COOKIES, results):
        expected = cookie.get("expected_category")
        if expected:
            total += 1
            if result.category == expected:
                correct += 1

        if result.requires_review:
            low_confidence_count += 1

    # Print results
    for cookie, result in zip(TEST_COOKIES, results):
        print_classification_result(
            cookie, result, cookie.get("expected_category")
        )

    # Summary
    print(f"\n{'=' * 70}")
    print("TEST SUMMARY")
    print(f"{'=' * 70}")
    if total > 0:
        accuracy = (correct / total) * 100
        print(f"Accuracy: {correct}/{total} ({accuracy:.1f}%)")
    print(f"Low confidence predictions: {low_confidence_count}/{len(TEST_COOKIES)}")
    print(f"Average confidence: {sum(r.confidence for r in results) / len(results):.1%}")
    print(f"{'=' * 70}")


def interactive_mode(classifier: MLCookieClassifier):
    """Interactive mode for manual cookie testing."""
    print("\n" + "=" * 70)
    print("INTERACTIVE COOKIE CLASSIFIER")
    print("=" * 70)
    print("Enter cookie details (or 'quit' to exit)\n")

    while True:
        try:
            name = input("Cookie name: ").strip()
            if name.lower() in ["quit", "exit", "q"]:
                break

            domain = input("Domain (e.g., .example.com): ").strip() or ".example.com"
            duration = input("Duration (e.g., '365 days' or 'Session'): ").strip() or "Session"
            cookie_type = input("Type (First Party / Third Party): ").strip() or "First Party"

            # Build cookie dict
            cookie = {
                "name": name,
                "domain": domain,
                "cookie_duration": duration,
                "cookie_type": cookie_type,
                "httpOnly": False,
                "secure": True,
                "sameSite": "None" if cookie_type == "Third Party" else "Lax",
            }

            # Classify
            result = classifier.classify(cookie)
            print_classification_result(cookie, result)

            print("\n")

        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def main():
    """Main test workflow."""
    import argparse

    parser = argparse.ArgumentParser(description="Test cookie classifier")
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactive mode for manual testing",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("COOKIE CLASSIFIER TESTING")
    print("=" * 70)

    # Load classifier
    try:
        classifier = MLCookieClassifier()
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        print("\nPlease train the model first:")
        print("  python scripts/train_model.py")
        return

    # Show model info
    info = classifier.get_model_info()
    print(f"\nModel Version: {info['model_version']}")
    print(f"Model Type: {info['model_type']}")
    print(f"Categories: {', '.join(info['categories'])}")
    print(f"Feature Count: {info['feature_count']}")

    if args.interactive:
        interactive_mode(classifier)
    else:
        run_batch_test(classifier)


if __name__ == "__main__":
    main()
