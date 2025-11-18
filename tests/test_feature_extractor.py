"""
Unit Tests for FeatureExtractor

Tests feature extraction from cookie objects to ensure correctness.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from ml_classifier.feature_extractor import FeatureExtractor


@pytest.fixture
def extractor():
    """Fixture to create FeatureExtractor instance."""
    return FeatureExtractor()


class TestNameFeatures:
    """Test name-based feature extraction."""

    def test_name_length(self, extractor):
        cookie = {"name": "_ga"}
        features = extractor.extract(cookie)
        assert features["name_length"] == 3

        cookie = {"name": "very_long_cookie_name_here"}
        features = extractor.extract(cookie)
        assert features["name_length"] == 27

    def test_has_underscore(self, extractor):
        cookie = {"name": "_ga"}
        features = extractor.extract(cookie)
        assert features["has_underscore"] == 1

        cookie = {"name": "sessionid"}
        features = extractor.extract(cookie)
        assert features["has_underscore"] == 0

    def test_has_numbers(self, extractor):
        cookie = {"name": "session123"}
        features = extractor.extract(cookie)
        assert features["has_numbers"] == 1

        cookie = {"name": "language"}
        features = extractor.extract(cookie)
        assert features["has_numbers"] == 0

    def test_name_entropy(self, extractor):
        # Low entropy (structured name)
        cookie = {"name": "aaaaa"}
        features = extractor.extract(cookie)
        assert features["name_entropy"] < 0.2

        # High entropy (random-looking)
        cookie = {"name": "a1b2c3d4e5"}
        features = extractor.extract(cookie)
        assert features["name_entropy"] > 0.5

    def test_vendor_fingerprint(self, extractor):
        # Google
        cookie = {"name": "_ga"}
        features = extractor.extract(cookie)
        assert features["vendor_fingerprint"] == 1

        # Facebook
        cookie = {"name": "_fbp"}
        features = extractor.extract(cookie)
        assert features["vendor_fingerprint"] == 2

        # Session
        cookie = {"name": "sessionid"}
        features = extractor.extract(cookie)
        assert features["vendor_fingerprint"] == 5

        # Unknown
        cookie = {"name": "xyz_unknown"}
        features = extractor.extract(cookie)
        assert features["vendor_fingerprint"] == 0


class TestDomainFeatures:
    """Test domain-based feature extraction."""

    def test_domain_levels(self, extractor):
        cookie = {"name": "test", "domain": ".example.com"}
        features = extractor.extract(cookie)
        assert features["domain_levels"] == 2

        cookie = {"name": "test", "domain": ".www.example.com"}
        features = extractor.extract(cookie)
        assert features["domain_levels"] == 3

    def test_known_analytics(self, extractor):
        cookie = {"name": "test", "domain": ".google-analytics.com"}
        features = extractor.extract(cookie)
        assert features["is_known_analytics"] == 1

        cookie = {"name": "test", "domain": ".hotjar.com"}
        features = extractor.extract(cookie)
        assert features["is_known_analytics"] == 1

        cookie = {"name": "test", "domain": ".example.com"}
        features = extractor.extract(cookie)
        assert features["is_known_analytics"] == 0

    def test_known_advertising(self, extractor):
        cookie = {"name": "test", "domain": ".facebook.com"}
        features = extractor.extract(cookie)
        assert features["is_known_advertising"] == 1

        cookie = {"name": "test", "domain": ".doubleclick.net"}
        features = extractor.extract(cookie)
        assert features["is_known_advertising"] == 1

        cookie = {"name": "test", "domain": ".example.com"}
        features = extractor.extract(cookie)
        assert features["is_known_advertising"] == 0

    def test_is_cdn(self, extractor):
        cookie = {"name": "test", "domain": ".cloudflare.com"}
        features = extractor.extract(cookie)
        assert features["is_cdn"] == 1

        cookie = {"name": "test", "domain": ".example.com"}
        features = extractor.extract(cookie)
        assert features["is_cdn"] == 0


class TestDurationFeatures:
    """Test duration-based feature extraction."""

    def test_is_session(self, extractor):
        cookie = {"name": "test", "cookie_duration": "Session"}
        features = extractor.extract(cookie)
        assert features["is_session"] == 1
        assert features["duration_days"] == 0.0

        cookie = {"name": "test", "cookie_duration": "30 days"}
        features = extractor.extract(cookie)
        assert features["is_session"] == 0

    def test_duration_parsing(self, extractor):
        # Days
        cookie = {"name": "test", "cookie_duration": "30 days"}
        features = extractor.extract(cookie)
        assert features["duration_days"] == 30.0

        # Years
        cookie = {"name": "test", "cookie_duration": "2 years"}
        features = extractor.extract(cookie)
        assert features["duration_days"] == 730.0

        # Months
        cookie = {"name": "test", "cookie_duration": "3 months"}
        features = extractor.extract(cookie)
        assert features["duration_days"] == 90.0

    def test_duration_category(self, extractor):
        # Session
        cookie = {"name": "test", "cookie_duration": "Session"}
        features = extractor.extract(cookie)
        assert features["duration_category_encoded"] == 0

        # Short-term (<30 days)
        cookie = {"name": "test", "cookie_duration": "7 days"}
        features = extractor.extract(cookie)
        assert features["duration_category_encoded"] == 1

        # Medium-term (30-365 days)
        cookie = {"name": "test", "cookie_duration": "90 days"}
        features = extractor.extract(cookie)
        assert features["duration_category_encoded"] == 2

        # Long-term (>365 days)
        cookie = {"name": "test", "cookie_duration": "730 days"}
        features = extractor.extract(cookie)
        assert features["duration_category_encoded"] == 3


class TestSecurityFeatures:
    """Test security-related feature extraction."""

    def test_http_only(self, extractor):
        cookie = {"name": "test", "httpOnly": True}
        features = extractor.extract(cookie)
        assert features["httpOnly"] == 1

        cookie = {"name": "test", "httpOnly": False}
        features = extractor.extract(cookie)
        assert features["httpOnly"] == 0

    def test_secure(self, extractor):
        cookie = {"name": "test", "secure": True}
        features = extractor.extract(cookie)
        assert features["secure"] == 1

        cookie = {"name": "test", "secure": False}
        features = extractor.extract(cookie)
        assert features["secure"] == 0

    def test_same_site(self, extractor):
        cookie = {"name": "test", "sameSite": "Strict"}
        features = extractor.extract(cookie)
        assert features["sameSite_encoded"] == 2

        cookie = {"name": "test", "sameSite": "Lax"}
        features = extractor.extract(cookie)
        assert features["sameSite_encoded"] == 1

        cookie = {"name": "test", "sameSite": "None"}
        features = extractor.extract(cookie)
        assert features["sameSite_encoded"] == 0

    def test_security_score(self, extractor):
        # High security
        cookie = {
            "name": "test",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Strict",
        }
        features = extractor.extract(cookie)
        assert features["security_score"] == 1.0

        # Low security
        cookie = {
            "name": "test",
            "httpOnly": False,
            "secure": False,
            "sameSite": "None",
        }
        features = extractor.extract(cookie)
        assert features["security_score"] == 0.0


class TestBehavioralFeatures:
    """Test behavioral feature extraction."""

    def test_is_third_party(self, extractor):
        cookie = {"name": "test", "cookie_type": "Third Party"}
        features = extractor.extract(cookie)
        assert features["is_third_party"] == 1

        cookie = {"name": "test", "cookie_type": "First Party"}
        features = extractor.extract(cookie)
        assert features["is_third_party"] == 0

    def test_size(self, extractor):
        cookie = {"name": "test", "size": 50}
        features = extractor.extract(cookie)
        assert features["size"] == 50

    def test_set_after_accept(self, extractor):
        cookie = {"name": "test", "set_after_accept": True}
        features = extractor.extract(cookie)
        assert features["set_after_accept"] == 1

        cookie = {"name": "test", "set_after_accept": False}
        features = extractor.extract(cookie)
        assert features["set_after_accept"] == 0

    def test_path_is_root(self, extractor):
        cookie = {"name": "test", "path": "/"}
        features = extractor.extract(cookie)
        assert features["path_is_root"] == 1

        cookie = {"name": "test", "path": "/api"}
        features = extractor.extract(cookie)
        assert features["path_is_root"] == 0


class TestPatternFeatures:
    """Test pattern matching features."""

    def test_analytics_pattern(self, extractor):
        cookie = {"name": "_ga"}
        features = extractor.extract(cookie)
        assert features["matches_analytics_pattern"] == 1

        cookie = {"name": "_hjid"}
        features = extractor.extract(cookie)
        assert features["matches_analytics_pattern"] == 1

        cookie = {"name": "sessionid"}
        features = extractor.extract(cookie)
        assert features["matches_analytics_pattern"] == 0

    def test_advertising_pattern(self, extractor):
        cookie = {"name": "_fbp"}
        features = extractor.extract(cookie)
        assert features["matches_advertising_pattern"] == 1

        cookie = {"name": "IDE"}
        features = extractor.extract(cookie)
        assert features["matches_advertising_pattern"] == 1

        cookie = {"name": "language"}
        features = extractor.extract(cookie)
        assert features["matches_advertising_pattern"] == 0

    def test_necessary_pattern(self, extractor):
        cookie = {"name": "sessionid"}
        features = extractor.extract(cookie)
        assert features["matches_necessary_pattern"] == 1

        cookie = {"name": "csrf_token"}
        features = extractor.extract(cookie)
        assert features["matches_necessary_pattern"] == 1

        cookie = {"name": "_ga"}
        features = extractor.extract(cookie)
        assert features["matches_necessary_pattern"] == 0

    def test_functional_pattern(self, extractor):
        cookie = {"name": "language"}
        features = extractor.extract(cookie)
        assert features["matches_functional_pattern"] == 1

        cookie = {"name": "theme"}
        features = extractor.extract(cookie)
        assert features["matches_functional_pattern"] == 1

        cookie = {"name": "_ga"}
        features = extractor.extract(cookie)
        assert features["matches_functional_pattern"] == 0


class TestBatchExtraction:
    """Test batch feature extraction."""

    def test_batch_extract(self, extractor):
        cookies = [
            {"name": "_ga", "domain": ".google-analytics.com"},
            {"name": "sessionid", "domain": ".example.com"},
            {"name": "_fbp", "domain": ".facebook.com"},
        ]

        features_df = extractor.extract_batch(cookies)

        assert len(features_df) == 3
        assert "name_length" in features_df.columns
        assert "is_third_party" in features_df.columns


class TestCompleteExtraction:
    """Test complete feature extraction for real-world cookies."""

    def test_google_analytics_cookie(self, extractor):
        cookie = {
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
        }

        features = extractor.extract(cookie)

        # Name features
        assert features["name_length"] == 3
        assert features["has_underscore"] == 1
        assert features["vendor_fingerprint"] == 1  # Google

        # Domain features
        assert features["is_known_analytics"] == 1
        assert features["is_third_party"] == 1

        # Duration features
        assert features["duration_days"] == 730.0
        assert features["duration_category_encoded"] == 3  # Long-term

        # Security features
        assert features["httpOnly"] == 0
        assert features["secure"] == 1

        # Pattern features
        assert features["matches_analytics_pattern"] == 1

    def test_session_cookie(self, extractor):
        cookie = {
            "name": "sessionid",
            "domain": ".example.com",
            "cookie_duration": "Session",
            "cookie_type": "First Party",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Strict",
        }

        features = extractor.extract(cookie)

        assert features["is_session"] == 1
        assert features["duration_days"] == 0.0
        assert features["is_third_party"] == 0
        assert features["httpOnly"] == 1
        assert features["security_score"] == 1.0
        assert features["matches_necessary_pattern"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
