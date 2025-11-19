"""
Test script to verify cookie categorization integration.
"""

import asyncio
import logging
from src.services.cookie_categorization import (
    categorize_cookie,
    initialize_categorization,
    hash_cookie_value,
    cookie_duration_days,
    determine_party_type
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_hash_cookie_value():
    """Test cookie value hashing."""
    print("\n=== Testing Cookie Value Hashing ===")
    
    test_value = "test_cookie_value_123"
    hashed = hash_cookie_value(test_value)
    
    print(f"Original: {test_value}")
    print(f"Hashed: {hashed}")
    print(f"Hash length: {len(hashed)}")
    
    assert hashed is not None
    assert len(hashed) == 64  # SHA-256 produces 64 hex characters
    print("✓ Cookie value hashing works correctly")


def test_cookie_duration():
    """Test cookie duration calculation."""
    print("\n=== Testing Cookie Duration ===")
    
    import time
    from datetime import datetime, timezone
    
    # Session cookie
    duration = cookie_duration_days(None)
    print(f"Session cookie: {duration}")
    assert duration == "Session"
    
    # Expired cookie
    past_timestamp = time.time() - 86400  # 1 day ago
    duration = cookie_duration_days(past_timestamp)
    print(f"Expired cookie: {duration}")
    assert duration == "Expired"
    
    # Future cookie (30 days)
    future_timestamp = time.time() + (30 * 86400)
    duration = cookie_duration_days(future_timestamp)
    print(f"30-day cookie: {duration}")
    assert "days" in duration
    
    print("✓ Cookie duration calculation works correctly")


def test_party_type():
    """Test party type determination."""
    print("\n=== Testing Party Type Determination ===")
    
    # First party
    party = determine_party_type(".example.com", "https://example.com")
    print(f"Same domain: {party}")
    assert party == "First Party"
    
    # Third party
    party = determine_party_type(".google-analytics.com", "https://example.com")
    print(f"Different domain: {party}")
    assert party == "Third Party"
    
    print("✓ Party type determination works correctly")


def test_categorize_cookie():
    """Test cookie categorization."""
    print("\n=== Testing Cookie Categorization ===")
    
    # Initialize categorization system
    initialize_categorization()
    
    # Test with a common cookie name
    test_cookies = [
        {
            "name": "_ga",
            "domain": ".example.com",
            "path": "/",
            "value": "GA1.2.123456789.1234567890"
        },
        {
            "name": "session_id",
            "domain": ".example.com",
            "path": "/",
            "value": "abc123def456"
        },
        {
            "name": "unknown_cookie_xyz",
            "domain": ".example.com",
            "path": "/",
            "value": "some_value"
        }
    ]
    
    for cookie_data in test_cookies:
        result = categorize_cookie(
            name=cookie_data["name"],
            domain_config_id="test_domain_config_id",
            cookie_data=cookie_data
        )
        
        print(f"\nCookie: {cookie_data['name']}")
        print(f"  Category: {result.get('category')}")
        print(f"  Vendor: {result.get('vendor')}")
        print(f"  Source: {result.get('source')}")
        print(f"  Description: {result.get('description')}")
        print(f"  Requires Review: {result.get('requires_review')}")
        
        # Verify required fields are present
        assert 'category' in result
        assert 'vendor' in result
        assert 'source' in result
        assert 'iab_purposes' in result
        assert 'description' in result
        assert 'requires_review' in result
    
    print("\n✓ Cookie categorization works correctly")


def test_categorization_with_metadata():
    """Test that categorization includes ML metadata."""
    print("\n=== Testing Categorization with ML Metadata ===")
    
    cookie_data = {
        "name": "_fbp",
        "domain": ".facebook.com",
        "path": "/",
        "value": "fb.1.1234567890.123456789"
    }
    
    result = categorize_cookie(
        name=cookie_data["name"],
        domain_config_id="test_domain_config_id",
        cookie_data=cookie_data
    )
    
    print(f"\nCookie: {cookie_data['name']}")
    print(f"  Category: {result.get('category')}")
    print(f"  Source: {result.get('source')}")
    print(f"  ML Confidence: {result.get('ml_confidence')}")
    print(f"  Classification Evidence: {result.get('classification_evidence')}")
    
    # Verify metadata fields
    assert 'ml_confidence' in result
    assert 'ml_probabilities' in result
    assert 'classification_evidence' in result
    
    print("\n✓ Categorization includes ML metadata")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Cookie Categorization Integration Tests")
    print("=" * 60)
    
    try:
        test_hash_cookie_value()
        test_cookie_duration()
        test_party_type()
        test_categorize_cookie()
        test_categorization_with_metadata()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"✗ Test failed: {e}")
        print("=" * 60)
        raise


if __name__ == "__main__":
    main()
