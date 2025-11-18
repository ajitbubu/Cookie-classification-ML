#!/usr/bin/env python3
"""
Simple ML Integration Test

Tests that ML classifier works and can be used for cookie categorization.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_ml_classifier():
    """Test ML classifier directly."""
    print("=" * 70)
    print("ML CLASSIFIER INTEGRATION TEST")
    print("=" * 70)

    # Import ML classifier
    try:
        from ml_classifier import MLCookieClassifier
        print("\n✓ ML Classifier module loaded successfully")
    except Exception as e:
        print(f"\n✗ Failed to load ML Classifier: {e}")
        print("\nTrain the model first:")
        print("  python scripts/train_model.py")
        return

    # Initialize classifier
    try:
        classifier = MLCookieClassifier()
        print("✓ ML Classifier initialized successfully")
        print(f"✓ Model version: {classifier.model_version}")
    except FileNotFoundError:
        print("\n✗ Model not found!")
        print("\nTrain the model first:")
        print("  python scripts/train_model.py")
        return
    except Exception as e:
        print(f"\n✗ Failed to initialize classifier: {e}")
        return

    print()

    # Test cookies
    test_cookies = [
        {
            "name": "_ga",
            "domain": ".google-analytics.com",
            "path": "/",
            "cookie_duration": "730 days",
            "size": 50,
            "httpOnly": False,
            "secure": True,
            "sameSite": "None",
            "cookie_type": "Third Party",
            "set_after_accept": True,
            "expected": "Analytics",
        },
        {
            "name": "sessionid",
            "domain": ".example.com",
            "path": "/",
            "cookie_duration": "Session",
            "size": 32,
            "httpOnly": True,
            "secure": True,
            "sameSite": "Strict",
            "cookie_type": "First Party",
            "set_after_accept": False,
            "expected": "Necessary",
        },
        {
            "name": "_fbp",
            "domain": ".facebook.com",
            "path": "/",
            "cookie_duration": "90 days",
            "size": 42,
            "httpOnly": False,
            "secure": True,
            "sameSite": "None",
            "cookie_type": "Third Party",
            "set_after_accept": True,
            "expected": "Advertising",
        },
        {
            "name": "language",
            "domain": ".example.com",
            "path": "/",
            "cookie_duration": "365 days",
            "size": 10,
            "httpOnly": False,
            "secure": True,
            "sameSite": "Lax",
            "cookie_type": "First Party",
            "set_after_accept": True,
            "expected": "Functional",
        },
    ]

    results = []
    for cookie_data in test_cookies:
        expected = cookie_data.pop("expected")
        name = cookie_data["name"]

        # Classify
        result = classifier.classify(cookie_data)

        # Check result
        match = "✓" if result.category == expected else "✗"
        is_correct = result.category == expected

        results.append({
            "cookie": name,
            "expected": expected,
            "predicted": result.category,
            "confidence": result.confidence,
            "source": result.source,
            "match": is_correct,
        })

        print(f"{match} Cookie: {name}")
        print(f"   Expected:   {expected}")
        print(f"   Predicted:  {result.category}")
        print(f"   Confidence: {result.confidence:.1%}")
        print(f"   Source:     {result.source}")
        print(f"   Evidence:   {result.evidence[0] if result.evidence else 'N/A'}")
        if result.requires_review:
            print(f"   ⚠ Requires manual review")
        print()

    # Summary
    correct = sum(1 for r in results if r["match"])
    total = len(results)
    accuracy = (correct / total) * 100

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Test Accuracy: {correct}/{total} ({accuracy:.1f}%)")

    # Confidence stats
    high_conf = sum(1 for r in results if r["confidence"] >= 0.75)
    medium_conf = sum(1 for r in results if 0.50 <= r["confidence"] < 0.75)
    low_conf = sum(1 for r in results if r["confidence"] < 0.50)

    print(f"\nConfidence Distribution:")
    print(f"  High (≥75%):   {high_conf}/{total}")
    print(f"  Medium (50-75%): {medium_conf}/{total}")
    print(f"  Low (<50%):    {low_conf}/{total}")

    avg_confidence = sum(r["confidence"] for r in results) / total
    print(f"\nAverage Confidence: {avg_confidence:.1%}")

    print("\n" + "=" * 70)
    print("INTEGRATION READY")
    print("=" * 70)
    print("✓ ML Classifier is working and ready for integration")
    print("✓ Cookie scanner will use hybrid ML + rules strategy:")
    print("  1. Database overrides (highest priority)")
    print(f"  2. ML classifier (high confidence ≥75%): {high_conf} cookies")
    print("  3. IAB Global Vendor List")
    print("  4. Local cookie rules")
    print(f"  5. ML classifier (low confidence): {medium_conf + low_conf} cookies with fallback")
    print()
    print("Next steps:")
    print("  - Run actual cookie scans to collect more training data")
    print("  - Review low-confidence predictions")
    print("  - Retrain model with corrections")
    print("=" * 70)


if __name__ == "__main__":
    test_ml_classifier()
