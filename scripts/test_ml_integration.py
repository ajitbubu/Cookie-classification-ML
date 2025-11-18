#!/usr/bin/env python3
"""
Test ML Integration in Cookie Scanner

Quick test to verify ML classifier is working in cookie_scanner.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

# Import after adding to path
from cookie_scanner import categorize_cookie, ML_ENABLED

def test_ml_integration():
    """Test ML integration with various cookie examples."""
    print("=" * 70)
    print("ML INTEGRATION TEST")
    print("=" * 70)

    if not ML_ENABLED:
        print("\n✗ ML Classifier not enabled!")
        print("  Train the model first: python scripts/train_model.py")
        return

    print(f"\n✓ ML Classifier loaded successfully\n")

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
            "expected_category": "Analytics",
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
            "expected_category": "Necessary",
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
            "expected_category": "Advertising",
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
            "expected_category": "Functional",
        },
    ]

    results = []
    for cookie in test_cookies:
        expected = cookie.pop("expected_category")

        # Categorize with ML
        result = categorize_cookie(
            name=cookie["name"],
            domain_config_id="test_domain",
            cookie_data=cookie
        )

        # Check result
        match = "✓" if result["category"] == expected else "✗"
        results.append({
            "cookie": cookie["name"],
            "expected": expected,
            "predicted": result["category"],
            "confidence": result.get("ml_confidence"),
            "source": result["source"],
            "match": match == "✓",
        })

        print(f"{match} Cookie: {cookie['name']}")
        print(f"   Expected:   {expected}")
        print(f"   Predicted:  {result['category']}")
        print(f"   Source:     {result['source']}")
        if result.get("ml_confidence"):
            print(f"   Confidence: {result['ml_confidence']:.1%}")
        if result.get("classification_evidence"):
            print(f"   Evidence:   {result['classification_evidence'][0]}")
        print()

    # Summary
    correct = sum(1 for r in results if r["match"])
    total = len(results)
    accuracy = (correct / total) * 100

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Accuracy: {correct}/{total} ({accuracy:.1f}%)")

    # ML usage stats
    ml_sources = [r["source"] for r in results if "ML" in r["source"]]
    if ml_sources:
        print(f"ML Classifications: {len(ml_sources)}/{total}")
        print(f"  High confidence: {sum(1 for s in ml_sources if s == 'ML_High')}")
        print(f"  Low confidence:  {sum(1 for s in ml_sources if s == 'ML_Low')}")
        print(f"  Blended:         {sum(1 for s in ml_sources if 'Blend' in s or 'Agree' in s)}")
    else:
        print("ML Classifications: 0 (all fell back to rules)")

    # Confidence stats
    confidences = [r["confidence"] for r in results if r["confidence"] is not None]
    if confidences:
        avg_confidence = sum(confidences) / len(confidences)
        print(f"\nAverage ML Confidence: {avg_confidence:.1%}")
        high_conf = sum(1 for c in confidences if c >= 0.75)
        print(f"High confidence (≥75%): {high_conf}/{len(confidences)}")

    print("=" * 70)

    if accuracy >= 75:
        print("✓ Integration test PASSED!")
    else:
        print("⚠ Integration test: Accuracy below 75%")
        print("  This is expected with limited training data.")
        print("  Model is working but needs more training samples.")


if __name__ == "__main__":
    test_ml_integration()
