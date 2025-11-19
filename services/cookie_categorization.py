"""
Cookie categorization service with multi-tier classification.

This module provides cookie categorization using a hybrid approach:
1. DB overrides (per-domain, highest priority)
2. ML classifier (if confidence >= 75%)
3. IAB vendor mapping (via iab_id in cookie rules)
4. Local cookie_rules.json regex rules
5. ML classifier (low confidence, with warning)
6. Default fallback
"""

import hashlib
import json
import logging
import re
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from config import (
    FETCH_COOKIE_CATEGORIZATION_API_URL,
    IAB_PURPOSE_CATEGORY_MAP,
    IAB_GVL_URL,
    CATEGORY_PRIORITY,
    REQUEST_TIMEOUT
)

logger = logging.getLogger(__name__)

# Global cache for IAB GVL and DB overrides
GVL_CACHE_FILE = Path(__file__).parent.parent / "iab_gvl.json"
DOMAIN_COOKIE_CATEGORIZATION_FROM_DB: Dict[str, Dict[str, Any]] = {}
GVL: Dict[str, Any] = {}
COOKIE_RULES: List[Dict[str, Any]] = []

# ML Classifier (optional)
ML_CLASSIFIER = None
ML_ENABLED = False

try:
    from ml_classifier import MLCookieClassifier
    ML_CLASSIFIER = MLCookieClassifier()
    ML_ENABLED = True
    logger.info("✓ ML Cookie Classifier loaded successfully")
except Exception as e:
    logger.warning(f"ML Cookie Classifier not available: {e}. Using rules-only classification.")


def initialize_categorization():
    """Initialize categorization system by loading rules and GVL."""
    global COOKIE_RULES, GVL
    
    # Load cookie rules
    rules_file = Path(__file__).parent.parent / "cookie_rules.json"
    try:
        with open(rules_file, encoding="utf-8") as f:
            rules_raw = json.load(f).get("rules", [])
            COOKIE_RULES = [
                {
                    "pattern": re.compile(rule.get("pattern", "^$") or "^$", re.IGNORECASE),
                    "category": rule.get("category", "Unknown"),
                    "iab_purposes": rule.get("iab_purposes", []),
                    "description": rule.get("description", ""),
                    "domains": [d.lower() for d in rule.get("domains", [])],
                    "iab_id": rule.get("iab_id"),
                    "vendor": rule.get("vendor", ""),
                }
                for rule in rules_raw
            ]
        logger.info(f"Loaded {len(COOKIE_RULES)} cookie rules")
    except Exception as e:
        logger.error(f"Failed to load cookie rules: {e}")
        COOKIE_RULES = []
    
    # Load IAB GVL
    GVL = load_iab_vendor_list()


def load_iab_vendor_list(force_refresh: bool = False) -> Dict[str, Any]:
    """Load IAB Global Vendor List (GVL) and cache it locally."""
    if not force_refresh and GVL_CACHE_FILE.exists():
        try:
            return json.loads(GVL_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("GVL cache file unreadable, attempting remote fetch")
    
    try:
        resp = requests.get(IAB_GVL_URL, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        gvl = resp.json()
        try:
            GVL_CACHE_FILE.write_text(json.dumps(gvl, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Unable to write GVL cache file: {e}")
        return gvl
    except Exception as e:
        logger.warning(f"Failed to fetch IAB GVL: {e}")
        if GVL_CACHE_FILE.exists():
            try:
                return json.loads(GVL_CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                logger.error("GVL cache exists but cannot be read")
        return {}


def load_db_cookie_categorization_for_domain(domain_config_id: str) -> Dict[str, Any]:
    """Fetch cookie categorization overrides from remote API and cache per domain."""
    try:
        logger.info(f"Fetching DB categorization data for domain_config_id {domain_config_id}")
        response = requests.get(
            f"{FETCH_COOKIE_CATEGORIZATION_API_URL}?domain_config_id={domain_config_id}",
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json() or {}
        
        if isinstance(data, dict) and "data" in data:
            resp_data = data["data"]
            if resp_data:
                resp_domain_config_id = resp_data.get("domain_config_id")
                if resp_domain_config_id == domain_config_id:
                    cookies_list = resp_data.get("cookies", [])
                    cookies_dict = {c.get("name"): c for c in cookies_list if "name" in c}
                    DOMAIN_COOKIE_CATEGORIZATION_FROM_DB[domain_config_id] = cookies_dict
                else:
                    DOMAIN_COOKIE_CATEGORIZATION_FROM_DB[domain_config_id] = {}
            else:
                DOMAIN_COOKIE_CATEGORIZATION_FROM_DB[domain_config_id] = {}
    except Exception as e:
        logger.error(f"Failed to load DB categorization for {domain_config_id}: {e}")
        DOMAIN_COOKIE_CATEGORIZATION_FROM_DB[domain_config_id] = {}
    
    return DOMAIN_COOKIE_CATEGORIZATION_FROM_DB[domain_config_id]


def map_purposes_to_category(purposes: List[int]) -> str:
    """Map a list of IAB purposes to a CMP category using CATEGORY_PRIORITY."""
    mapped = {IAB_PURPOSE_CATEGORY_MAP[p] for p in purposes if p in IAB_PURPOSE_CATEGORY_MAP}
    for cat in CATEGORY_PRIORITY:
        if cat in mapped:
            return cat
    return "Unknown"


def categorize_cookie(
    name: str,
    domain_config_id: str,
    cookie_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Categorize a cookie using hybrid ML + rules approach.
    
    Priority order:
    1) DB overrides (per-domain, highest priority)
    2) ML classifier (if confidence >= 75%)
    3) IAB vendor mapping (via iab_id in cookie rules)
    4) Local cookie_rules.json regex rules
    5) ML classifier (low confidence, with warning)
    6) Default fallback
    
    Args:
        name: Cookie name
        domain_config_id: Domain configuration ID
        cookie_data: Complete cookie dictionary (for ML classification)
    
    Returns:
        Dict with keys: category, vendor, iab_purposes, description, source,
                       ml_confidence, ml_probabilities, classification_evidence, requires_review
    """
    if name is None:
        name = ""
    
    # 1) DB overrides (if present in cache) - HIGHEST PRIORITY
    overrides = DOMAIN_COOKIE_CATEGORIZATION_FROM_DB.get(domain_config_id)
    if overrides is not None:
        categorized_cookie = overrides.get(name)
        if categorized_cookie:
            logger.info(f"Found cookie in DB overrides for domain {domain_config_id}: {name}")
            return {
                "category": categorized_cookie.get("category", "Unknown"),
                "vendor": categorized_cookie.get("vendor", ""),
                "iab_purposes": categorized_cookie.get("iab_purposes", []),
                "description": categorized_cookie.get("description", ""),
                "source": "DB",
                "ml_confidence": None,
                "ml_probabilities": None,
                "classification_evidence": ["Database override (highest priority)"],
                "requires_review": False,
            }
    
    # 2) Try ML classifier first (if enabled and cookie_data available)
    ml_result = None
    if ML_ENABLED and cookie_data is not None:
        try:
            ml_result = ML_CLASSIFIER.classify(cookie_data)
            
            # High confidence ML prediction (>= 75%)
            if ml_result.confidence >= 0.75:
                logger.info(f"ML high-confidence classification for {name}: {ml_result.category} ({ml_result.confidence:.1%})")
                return {
                    "category": ml_result.category,
                    "vendor": _extract_vendor_from_ml(cookie_data),
                    "iab_purposes": [],
                    "description": f"ML classified with {ml_result.confidence:.1%} confidence",
                    "source": "ML_High",
                    "ml_confidence": ml_result.confidence,
                    "ml_probabilities": ml_result.probabilities,
                    "classification_evidence": ml_result.evidence,
                    "requires_review": ml_result.requires_review,
                }
        except Exception as e:
            logger.warning(f"ML classification failed for {name}: {e}")
            ml_result = None
    
    # Normalize name for regex matching
    name_l = name.lower()
    
    # 3) IAB mapping (check rules that match the cookie name and have iab_id)
    for rule in COOKIE_RULES:
        if rule["pattern"].match(name_l):
            iab_id = rule.get("iab_id")
            if iab_id and isinstance(GVL, dict) and "vendors" in GVL and str(iab_id) in GVL["vendors"]:
                vendor = GVL["vendors"][str(iab_id)]
                purposes = vendor.get("purposes", [])
                mapped_category = map_purposes_to_category(purposes)
                
                result = {
                    "category": mapped_category,
                    "vendor": vendor.get("name", ""),
                    "iab_purposes": purposes,
                    "description": f"Cookie managed by {vendor.get('name', 'Unknown')}",
                    "source": "IAB",
                    "ml_confidence": None,
                    "ml_probabilities": None,
                    "classification_evidence": [f"IAB Global Vendor List: {vendor.get('name', 'Unknown')}"],
                    "requires_review": False,
                }
                
                # Add ML info if available
                if ml_result is not None:
                    result["ml_confidence"] = ml_result.confidence
                    result["ml_probabilities"] = ml_result.probabilities
                    result["classification_evidence"].extend(ml_result.evidence)
                    if ml_result.confidence >= 0.50:
                        result["source"] = "IAB_ML_Blend"
                
                return result
    
    # 4) Local JSON rules (manual classification)
    for rule in COOKIE_RULES:
        if rule["pattern"].match(name_l):
            result = {
                "category": rule["category"],
                "vendor": rule.get("vendor", ""),
                "iab_purposes": rule.get("iab_purposes", []),
                "description": rule.get("description", ""),
                "source": "RulesJSON",
                "ml_confidence": None,
                "ml_probabilities": None,
                "classification_evidence": [f"Pattern match: {rule.get('description', 'Local rule')}"],
                "requires_review": False,
            }
            
            # Add ML info if available
            if ml_result is not None:
                result["ml_confidence"] = ml_result.confidence
                result["ml_probabilities"] = ml_result.probabilities
                result["classification_evidence"].extend(ml_result.evidence)
                
                # If ML had medium confidence and agrees, boost confidence
                if ml_result.confidence >= 0.50 and ml_result.category == rule["category"]:
                    result["source"] = "Rules_ML_Agree"
                    result["classification_evidence"].insert(0, f"ML agrees ({ml_result.confidence:.1%} confidence)")
            
            return result
    
    # 5) ML classifier with low confidence (better than nothing)
    if ml_result is not None:
        logger.info(f"Using low-confidence ML prediction for {name}: {ml_result.category} ({ml_result.confidence:.1%})")
        return {
            "category": ml_result.category,
            "vendor": _extract_vendor_from_ml(cookie_data),
            "iab_purposes": [],
            "description": f"ML classified with LOW confidence ({ml_result.confidence:.1%})",
            "source": "ML_Low",
            "ml_confidence": ml_result.confidence,
            "ml_probabilities": ml_result.probabilities,
            "classification_evidence": ml_result.evidence + ["⚠ Low confidence - manual review recommended"],
            "requires_review": True,
        }
    
    # 6) Default fallback (no classification available)
    return {
        "category": "Unknown",
        "vendor": "Unknown",
        "iab_purposes": [],
        "description": "No classification available",
        "source": "Fallback",
        "ml_confidence": None,
        "ml_probabilities": None,
        "classification_evidence": ["No matching rules or patterns found"],
        "requires_review": True,
    }


def _extract_vendor_from_ml(cookie_data: Dict[str, Any]) -> str:
    """Extract vendor name from cookie domain or return 'Unknown'."""
    domain = cookie_data.get("domain", "")
    if not domain:
        return "Unknown"
    
    # Clean domain
    domain = domain.lstrip(".").lower()
    
    # Known vendor mappings
    vendor_map = {
        "google-analytics.com": "Google Analytics",
        "googletagmanager.com": "Google Tag Manager",
        "doubleclick.net": "Google DoubleClick",
        "facebook.com": "Facebook",
        "facebook.net": "Facebook",
        "hotjar.com": "Hotjar",
        "mixpanel.com": "Mixpanel",
        "linkedin.com": "LinkedIn",
        "clarity.ms": "Microsoft Clarity",
        "cloudflare.com": "Cloudflare",
    }
    
    for vendor_domain, vendor_name in vendor_map.items():
        if vendor_domain in domain:
            return vendor_name
    
    return "Unknown"


def hash_cookie_value(val: Optional[str]) -> Optional[str]:
    """Return SHA256 hash of a cookie value (None => None)."""
    if val is None:
        return None
    if not isinstance(val, str):
        val = str(val)
    return hashlib.sha256(val.encode("utf-8")).hexdigest()


def cookie_duration_days(expiry_ts) -> str:
    """
    Convert cookie expiry timestamp (Unix seconds) to a human-readable duration.
    
    Args:
        expiry_ts: float/int timestamp in seconds OR None/-1 for session cookies
    
    Returns:
        str: human-readable duration
    """
    if not expiry_ts or expiry_ts == -1:
        return "Session"
    
    try:
        now_ts = datetime.now(timezone.utc).timestamp()
        delta_seconds = float(expiry_ts) - now_ts
        
        if delta_seconds <= 0:
            return "Expired"
        elif delta_seconds < 24 * 3600:  # less than 1 day
            minutes = delta_seconds / 60
            return f"{minutes:.0f} minutes"
        else:
            days = delta_seconds / (24 * 3600)
            return f"{days:.1f} days"
    except Exception:
        return "Unknown"


def get_base_domain(domain: str) -> str:
    """Return registrar base domain (e.g. example.com)."""
    parts = domain.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain


def determine_party_type(cookie_domain: Optional[str], site_url: str) -> str:
    """Return 'First Party' if cookie_domain maps to site_url's base domain, else 'Third Party'."""
    if not cookie_domain:
        return "unknown"
    
    from urllib.parse import urlparse
    cookie_domain = cookie_domain.lstrip(".").lower()
    base_host = urlparse(site_url).hostname or site_url
    base_domain = get_base_domain(base_host.lower())
    return "First Party" if cookie_domain.endswith(base_domain) else "Third Party"


# Initialize on module load
initialize_categorization()
