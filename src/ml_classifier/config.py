"""
ML Classifier Configuration

Centralized configuration for ML model training, inference, and monitoring.
"""

from pathlib import Path
from typing import List, Dict

# Paths
BASE_DIR = Path(__file__).parent.parent
ML_DIR = BASE_DIR / "ml_classifier"
MODELS_DIR = BASE_DIR / "models"
TRAINING_DATA_DIR = BASE_DIR / "training_data"

# Ensure directories exist
MODELS_DIR.mkdir(exist_ok=True)
TRAINING_DATA_DIR.mkdir(exist_ok=True)

# Model files
MODEL_FILE = MODELS_DIR / "cookie_classifier_v1.pkl"
SCALER_FILE = MODELS_DIR / "feature_scaler.pkl"
LABEL_ENCODER_FILE = MODELS_DIR / "label_encoder.pkl"
METADATA_FILE = MODELS_DIR / "metadata.json"

# Training data files
TRAINING_CSV = TRAINING_DATA_DIR / "labeled_cookies.csv"
VALIDATION_CSV = TRAINING_DATA_DIR / "validation_cookies.csv"
TEST_CSV = TRAINING_DATA_DIR / "test_cookies.csv"

# Cookie categories (aligned with existing system)
COOKIE_CATEGORIES = [
    "Necessary",      # Strictly necessary for website operation
    "Functional",     # Functionality enhancements (language, theme)
    "Analytics",      # Analytics and performance tracking
    "Advertising",    # Advertising and marketing
]

# Category mapping to numeric labels
CATEGORY_TO_LABEL = {cat: idx for idx, cat in enumerate(COOKIE_CATEGORIES)}
LABEL_TO_CATEGORY = {idx: cat for idx, cat in enumerate(COOKIE_CATEGORIES)}

# Confidence thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.75   # Use ML prediction directly
MEDIUM_CONFIDENCE_THRESHOLD = 0.50  # Blend with rules
LOW_CONFIDENCE_THRESHOLD = 0.40     # Flag for manual review

# Feature extraction settings
KNOWN_ANALYTICS_DOMAINS = {
    "google-analytics.com",
    "googletagmanager.com",
    "doubleclick.net",
    "analytics.google.com",
    "hotjar.com",
    "mixpanel.com",
    "segment.com",
    "heap.io",
    "amplitude.com",
    "matomo.org",
}

KNOWN_ADVERTISING_DOMAINS = {
    "facebook.com",
    "facebook.net",
    "doubleclick.net",
    "googlesyndication.com",
    "adnxs.com",
    "adsrvr.org",
    "advertising.com",
    "criteo.com",
    "taboola.com",
    "outbrain.com",
}

KNOWN_CDN_DOMAINS = {
    "cloudflare.com",
    "cloudfront.net",
    "akamai.net",
    "fastly.net",
    "cdn77.com",
}

# Known cookie name patterns
ANALYTICS_PATTERNS = [
    "_ga", "_gid", "_gat", "ga_", "_utm",
    "_hjid", "_hjSessionUser", "_hjSession",
    "mp_", "mixpanel",
    "ajs_", "analytics",
    "heap", "_hp2_",
]

ADVERTISING_PATTERNS = [
    "_fbp", "_fbc", "fr",  # Facebook
    "IDE", "test_cookie", "_gcl",  # Google Ads
    "criteo", "uid", "uuid",
    "anj", "sess",  # AppNexus
]

NECESSARY_PATTERNS = [
    "session", "csrf", "xsrf",
    "auth", "token", "login",
    "consent", "cookie_consent",
    "PHPSESSID", "JSESSIONID",
]

FUNCTIONAL_PATTERNS = [
    "lang", "language", "locale",
    "theme", "currency",
    "timezone", "tz",
    "preference", "pref",
]

# Duration categories (in days)
DURATION_SHORT = 30      # < 30 days
DURATION_MEDIUM = 365    # 30-365 days
DURATION_LONG = 365      # > 365 days

# Model training hyperparameters
RANDOM_FOREST_PARAMS = {
    "n_estimators": 100,
    "max_depth": 15,
    "min_samples_split": 10,
    "min_samples_leaf": 5,
    "max_features": "sqrt",
    "class_weight": "balanced",  # Handle class imbalance
    "random_state": 42,
    "n_jobs": -1,  # Use all CPU cores
}

XGBOOST_PARAMS = {
    "n_estimators": 100,
    "max_depth": 8,
    "learning_rate": 0.1,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
}

# Training settings
TRAIN_TEST_SPLIT = 0.2  # 80% train, 20% test
VALIDATION_SPLIT = 0.1  # 10% of train for validation
CROSS_VALIDATION_FOLDS = 5

# Minimum samples per category
MIN_SAMPLES_PER_CATEGORY = 500

# Performance targets
TARGET_ACCURACY = 0.85          # Overall accuracy
TARGET_F1_SCORE = 0.80          # Per-class F1 score
TARGET_NECESSARY_PRECISION = 0.95  # High precision for compliance
TARGET_ADVERTISING_RECALL = 0.90   # High recall for privacy

# Model monitoring
ENABLE_MONITORING = True
LOG_PREDICTIONS = True
TRACK_CONFIDENCE_DISTRIBUTION = True

# Feature names (for reference)
FEATURE_NAMES = [
    # Name-based features
    "name_length",
    "has_underscore",
    "has_numbers",
    "has_uppercase",
    "name_entropy",
    "name_prefix_encoded",
    "name_suffix_encoded",
    "vendor_fingerprint",

    # Domain-based features
    "is_third_party",
    "domain_levels",
    "tld_encoded",
    "is_cdn",
    "is_known_analytics",
    "is_known_advertising",
    "domain_entropy",

    # Duration-based features
    "is_session",
    "duration_days",
    "duration_category_encoded",

    # Security features
    "httpOnly",
    "secure",
    "sameSite_encoded",
    "security_score",

    # Behavioral features
    "size",
    "set_after_accept",
    "path_is_root",

    # Pattern matching features
    "matches_analytics_pattern",
    "matches_advertising_pattern",
    "matches_necessary_pattern",
    "matches_functional_pattern",
]

# Expected feature count
EXPECTED_FEATURE_COUNT = len(FEATURE_NAMES)
