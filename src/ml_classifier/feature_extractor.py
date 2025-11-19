"""
Feature Extractor for Cookie Classification

Extracts 30+ ML features from cookie objects for classification.
Features include name patterns, domain characteristics, duration analysis,
security flags, and behavioral indicators.
"""

import re
import math
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import pandas as pd

from .config import (
    KNOWN_ANALYTICS_DOMAINS,
    KNOWN_ADVERTISING_DOMAINS,
    KNOWN_CDN_DOMAINS,
    ANALYTICS_PATTERNS,
    ADVERTISING_PATTERNS,
    NECESSARY_PATTERNS,
    FUNCTIONAL_PATTERNS,
    DURATION_SHORT,
    DURATION_MEDIUM,
)


class FeatureExtractor:
    """
    Extract machine learning features from cookie objects.

    Features extracted:
    - Name-based: length, character patterns, entropy, vendor fingerprints
    - Domain-based: party type, domain levels, TLD, reputation
    - Duration-based: session vs persistent, duration categories
    - Security: httpOnly, secure, sameSite flags
    - Behavioral: size, consent timing, path patterns
    """

    def __init__(self):
        """Initialize feature extractor with pattern matchers."""
        self.analytics_pattern = re.compile(
            "|".join(re.escape(p) for p in ANALYTICS_PATTERNS),
            re.IGNORECASE
        )
        self.advertising_pattern = re.compile(
            "|".join(re.escape(p) for p in ADVERTISING_PATTERNS),
            re.IGNORECASE
        )
        self.necessary_pattern = re.compile(
            "|".join(re.escape(p) for p in NECESSARY_PATTERNS),
            re.IGNORECASE
        )
        self.functional_pattern = re.compile(
            "|".join(re.escape(p) for p in FUNCTIONAL_PATTERNS),
            re.IGNORECASE
        )

        # Common TLDs for encoding
        self.common_tlds = {
            "com": 0, "net": 1, "org": 2, "io": 3, "co": 4,
            "uk": 5, "de": 6, "fr": 7, "jp": 8, "cn": 9,
        }

    def extract(self, cookie: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract all features from a cookie object.

        Args:
            cookie: Cookie dictionary with fields:
                - name: str
                - domain: str
                - path: str (optional)
                - cookie_duration: str (e.g., "Session", "365 days")
                - size: int (optional)
                - httpOnly: bool (optional)
                - secure: bool (optional)
                - sameSite: str (optional)
                - cookie_type: str (optional, "First Party" or "Third Party")
                - set_after_accept: bool (optional)

        Returns:
            Dictionary of extracted features ready for model input
        """
        features = {}

        # Extract individual feature groups
        features.update(self._extract_name_features(cookie.get("name", "")))
        features.update(self._extract_domain_features(cookie.get("domain", "")))
        features.update(self._extract_duration_features(cookie.get("cookie_duration", "Session")))
        features.update(self._extract_security_features(cookie))
        features.update(self._extract_behavioral_features(cookie))
        features.update(self._extract_pattern_features(cookie))

        return features

    def extract_batch(self, cookies: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Extract features from multiple cookies at once.

        Args:
            cookies: List of cookie dictionaries

        Returns:
            pandas DataFrame with features for all cookies
        """
        features_list = [self.extract(cookie) for cookie in cookies]
        return pd.DataFrame(features_list)

    def _extract_name_features(self, name: str) -> Dict[str, Any]:
        """Extract features from cookie name."""
        return {
            "name_length": len(name),
            "has_underscore": 1 if "_" in name else 0,
            "has_numbers": 1 if any(c.isdigit() for c in name) else 0,
            "has_uppercase": 1 if any(c.isupper() for c in name) else 0,
            "name_entropy": self._calculate_entropy(name),
            "name_prefix_encoded": self._encode_prefix(name),
            "name_suffix_encoded": self._encode_suffix(name),
            "vendor_fingerprint": self._extract_vendor_fingerprint(name),
        }

    def _extract_domain_features(self, domain: str) -> Dict[str, Any]:
        """Extract features from cookie domain."""
        # Clean domain (remove leading dot)
        clean_domain = domain.lstrip(".")

        # Count domain levels (e.g., "www.example.com" = 3)
        domain_levels = len(clean_domain.split("."))

        # Extract TLD
        tld = clean_domain.split(".")[-1] if "." in clean_domain else "unknown"
        tld_encoded = self.common_tlds.get(tld.lower(), 99)  # 99 for "other"

        # Check if domain is in known lists
        is_known_analytics = 1 if any(
            known in clean_domain.lower()
            for known in KNOWN_ANALYTICS_DOMAINS
        ) else 0

        is_known_advertising = 1 if any(
            known in clean_domain.lower()
            for known in KNOWN_ADVERTISING_DOMAINS
        ) else 0

        is_cdn = 1 if any(
            cdn in clean_domain.lower()
            for cdn in KNOWN_CDN_DOMAINS
        ) else 0

        return {
            "domain_levels": domain_levels,
            "tld_encoded": tld_encoded,
            "is_cdn": is_cdn,
            "is_known_analytics": is_known_analytics,
            "is_known_advertising": is_known_advertising,
            "domain_entropy": self._calculate_entropy(clean_domain),
        }

    def _extract_duration_features(self, duration_str: str) -> Dict[str, Any]:
        """Extract features from cookie duration."""
        is_session = 1 if duration_str.lower() == "session" else 0

        # Parse duration to days
        duration_days = self._parse_duration_to_days(duration_str)

        # Categorize duration
        if is_session:
            duration_category = 0  # Session
        elif duration_days <= DURATION_SHORT:
            duration_category = 1  # Short-term
        elif duration_days <= DURATION_MEDIUM:
            duration_category = 2  # Medium-term
        else:
            duration_category = 3  # Long-term

        return {
            "is_session": is_session,
            "duration_days": duration_days,
            "duration_category_encoded": duration_category,
        }

    def _extract_security_features(self, cookie: Dict[str, Any]) -> Dict[str, Any]:
        """Extract security-related features."""
        httpOnly = 1 if cookie.get("httpOnly", False) else 0
        secure = 1 if cookie.get("secure", False) else 0

        # Encode sameSite: Strict=2, Lax=1, None=0
        sameSite = cookie.get("sameSite", "None")
        if isinstance(sameSite, str):
            sameSite_encoded = {
                "strict": 2,
                "lax": 1,
                "none": 0,
            }.get(sameSite.lower(), 0)
        else:
            sameSite_encoded = 0

        # Calculate composite security score (0-1)
        security_score = (httpOnly + secure + (sameSite_encoded / 2)) / 3

        return {
            "httpOnly": httpOnly,
            "secure": secure,
            "sameSite_encoded": sameSite_encoded,
            "security_score": security_score,
        }

    def _extract_behavioral_features(self, cookie: Dict[str, Any]) -> Dict[str, Any]:
        """Extract behavioral features."""
        # Third-party detection
        cookie_type = cookie.get("cookie_type", "Unknown")
        is_third_party = 1 if cookie_type == "Third Party" else 0

        # Cookie size
        size = cookie.get("size", 0)

        # Consent timing
        set_after_accept = 1 if cookie.get("set_after_accept", False) else 0

        # Path analysis
        path = cookie.get("path", "/")
        path_is_root = 1 if path == "/" else 0

        return {
            "is_third_party": is_third_party,
            "size": size,
            "set_after_accept": set_after_accept,
            "path_is_root": path_is_root,
        }

    def _extract_pattern_features(self, cookie: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features based on pattern matching."""
        name = cookie.get("name", "")

        return {
            "matches_analytics_pattern": 1 if self.analytics_pattern.search(name) else 0,
            "matches_advertising_pattern": 1 if self.advertising_pattern.search(name) else 0,
            "matches_necessary_pattern": 1 if self.necessary_pattern.search(name) else 0,
            "matches_functional_pattern": 1 if self.functional_pattern.search(name) else 0,
        }

    def _calculate_entropy(self, text: str) -> float:
        """
        Calculate Shannon entropy of a string.
        Higher entropy = more random (e.g., tracking IDs).
        Lower entropy = more structured (e.g., session, language).
        """
        if not text:
            return 0.0

        # Count character frequencies
        char_counts = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1

        # Calculate entropy
        length = len(text)
        entropy = 0.0
        for count in char_counts.values():
            probability = count / length
            if probability > 0:
                entropy -= probability * math.log2(probability)

        # Normalize to 0-1 range (max entropy for ASCII is ~6.6)
        normalized_entropy = min(entropy / 6.6, 1.0)
        return round(normalized_entropy, 3)

    def _encode_prefix(self, name: str) -> int:
        """
        Encode first 3 characters of cookie name.
        Common prefixes: _ga, _fb, anj, uid, etc.
        """
        prefix = name[:3].lower() if len(name) >= 3 else name.lower()

        # Map common prefixes to integers
        prefix_map = {
            "_ga": 1, "_gi": 2, "_fb": 3, "_hj": 4,
            "mp_": 5, "ajs": 6, "uid": 7, "ses": 8,
            "csr": 9, "aut": 10, "tok": 11, "lan": 12,
            "ide": 13, "_gc": 14, "test": 15,
        }

        return prefix_map.get(prefix, 0)  # 0 for unknown

    def _encode_suffix(self, name: str) -> int:
        """
        Encode last 3 characters of cookie name.
        """
        suffix = name[-3:].lower() if len(name) >= 3 else name.lower()

        suffix_map = {
            "ion": 1, "sid": 2, "uid": 3, "tok": 4,
            "_id": 5, "ent": 6, "key": 7, "val": 8,
        }

        return suffix_map.get(suffix, 0)

    def _extract_vendor_fingerprint(self, name: str) -> int:
        """
        Extract vendor fingerprint from cookie name.
        Maps cookie names to known vendors.
        """
        name_lower = name.lower()

        # Google family
        if any(p in name_lower for p in ["_ga", "_gid", "_gat", "gac", "gcl"]):
            return 1  # Google

        # Facebook
        if any(p in name_lower for p in ["_fb", "fr_", "datr"]):
            return 2  # Facebook

        # Hotjar
        if "_hj" in name_lower:
            return 3  # Hotjar

        # Mixpanel
        if "mp_" in name_lower or "mixpanel" in name_lower:
            return 4  # Mixpanel

        # Session-like
        if "session" in name_lower or "sess" in name_lower:
            return 5  # Generic session

        # Auth-like
        if any(p in name_lower for p in ["auth", "token", "csrf", "xsrf"]):
            return 6  # Generic auth

        return 0  # Unknown

    def _parse_duration_to_days(self, duration_str: str) -> float:
        """
        Parse duration string to days.

        Examples:
            "Session" -> 0
            "30 days" -> 30.0
            "1 year" -> 365.0
            "2 months" -> 60.0
        """
        if not duration_str or duration_str.lower() == "session":
            return 0.0

        duration_lower = duration_str.lower()

        # Extract number
        numbers = re.findall(r"\d+\.?\d*", duration_lower)
        if not numbers:
            return 0.0

        value = float(numbers[0])

        # Determine unit
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
            # Assume days if no unit specified
            return value

    def get_feature_names(self) -> List[str]:
        """
        Get list of all feature names in order.

        Returns:
            List of feature names
        """
        from .config import FEATURE_NAMES
        return FEATURE_NAMES

    def validate_features(self, features: Dict[str, Any]) -> bool:
        """
        Validate that all expected features are present.

        Args:
            features: Extracted features dictionary

        Returns:
            True if valid, False otherwise
        """
        expected_features = set(self.get_feature_names())
        actual_features = set(features.keys())

        missing = expected_features - actual_features
        if missing:
            print(f"Warning: Missing features: {missing}")
            return False

        return True
