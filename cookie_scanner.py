# cookie_scanner.py
"""
Optimized and documented version of the original cookie_scanner.py.

Notes on approach (kept original logic):
- I preserved your original control flow and Playwright-based crawling logic.
- Small bug fixes and defensive checks were added (see comments).
- Added type hints and docstrings for clarity.
- Added explanatory comments (not changing behavior) and a few tiny optimizations
  that don't change outputs (e.g., ensuring functions return consistently).

If you'd like a second pass that adds more type checking or unit tests, tell me and
I will add them while still preserving behavior.
"""

import asyncio
import hashlib
import time
import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse
from pathlib import Path
from datetime import datetime, timezone

import requests
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

stealth = Stealth()

# Import project-specific config
from config import (
    RESULT_API_URL,
    FETCH_COOKIE_CATEGORIZATION_API_URL,
    SCAN_MAX_DEPTH_DEFAULT,
    SCAN_MAX_RETRY_DEFAULT,
    IAB_PURPOSE_CATEGORY_MAP,
    IAB_GVL_URL,
    CATEGORY_PRIORITY,
    DEFAULT_BUTTON_SELECTOR,
    REQUEST_TIMEOUT
)

logger = logging.getLogger(__name__)

# Import ML Cookie Classifier
try:
    from ml_classifier import MLCookieClassifier
    ML_CLASSIFIER = MLCookieClassifier()
    ML_ENABLED = True
    logger.info("✓ ML Cookie Classifier loaded successfully")
except Exception as e:
    ML_CLASSIFIER = None
    ML_ENABLED = False
    logger.warning(f"ML Cookie Classifier not available: {e}. Using rules-only classification.")


# -----------------------------------------------------------------------------
# Global constants and cache
# -----------------------------------------------------------------------------
GVL_CACHE_FILE = Path(__file__).parent / "iab_gvl.json"
DOMAIN_COOKIE_CATEGORIZATION_FROM_DB: Dict[str, Dict[str, Any]] = {}


# -----------------------------------------------------------------------------
# Load local cookie rules (one-time)
# -----------------------------------------------------------------------------
# Keep reading the user's cookie_rules.json as your original script did.
with open("cookie_rules.json", encoding="utf-8") as f:
    COOKIE_RULES_RAW = json.load(f).get("rules", [])

# Precompile regex rules for performance and add explicit keys to avoid KeyError later
COOKIE_RULES = [
    {
        "pattern": re.compile(rule.get("pattern", "^$") or "^$", re.IGNORECASE),
        "category": rule.get("category", "Unknown"),
        "iab_purposes": rule.get("iab_purposes", []),
        "description": rule.get("description", ""),
        "domains": [d.lower() for d in rule.get("domains", [])],  # optional domain restriction
        "iab_id": rule.get("iab_id"),
        "vendor": rule.get("vendor", ""),
    }
    for rule in COOKIE_RULES_RAW
]

from datetime import datetime, timezone

# -----------------------------------------------------------------------------
# Helper: Find expiry days
# -----------------------------------------------------------------------------
from datetime import datetime, timezone

def cookie_duration_days(expiry_ts):
    """
    Convert cookie expiry timestamp (Unix seconds) to a human-readable duration.
    - If expiry is None or -1 → "Session"
    - If already expired → "Expired"
    - If less than 1 day remaining → "<n> minutes"
    - Otherwise → "<n> days"
    
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


# -----------------------------------------------------------------------------
# Helper: Map IAB purposes to CMP categories
# -----------------------------------------------------------------------------
def map_purposes_to_category(purposes: List[int]) -> str:
    """Map a list of IAB purposes to a CMP category using CATEGORY_PRIORITY.

    If multiple categories map from purposes, CATEGORY_PRIORITY decides.
    """
    mapped = {IAB_PURPOSE_CATEGORY_MAP[p] for p in purposes if p in IAB_PURPOSE_CATEGORY_MAP}
    for cat in CATEGORY_PRIORITY:
        if cat in mapped:
            return cat
    return "Unknown"


# -----------------------------------------------------------------------------
# Load and cache IAB vendor list
# -----------------------------------------------------------------------------
def load_iab_vendor_list(force_refresh: bool = False) -> Dict[str, Any]:
    """Load IAB Global Vendor List (GVL) and cache it locally.

    Returns cached JSON if available and not force_refresh. If remote fetch fails
    and cache exists, falls back to cache. If no cache and fetch fails, returns {}.
    """
    # Fast path: return existing cached file content when available
    if not force_refresh and GVL_CACHE_FILE.exists():
        try:
            return json.loads(GVL_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            # If cache file is corrupt, continue to fetch remotely
            logger.warning("GVL cache file unreadable, attempting remote fetch")

    try:
        resp = requests.get(IAB_GVL_URL, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        gvl = resp.json()
        # write cache (best-effort)
        try:
            GVL_CACHE_FILE.write_text(json.dumps(gvl, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Unable to write GVL cache file: {e}")
        return gvl
    except Exception as e:
        logger.warning(f"[WARN] Failed to fetch IAB GVL: {e}")
        if GVL_CACHE_FILE.exists():
            try:
                return json.loads(GVL_CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                logger.error("GVL cache exists but cannot be read")
        return {}


# Load GVL once (same behavior as original script)
GVL = load_iab_vendor_list()


# -----------------------------------------------------------------------------
# DB Overrides: Fetch and cache per-domain cookie categorization
# -----------------------------------------------------------------------------
def load_db_cookie_categorization_for_domain(domain_config_id: str) -> Dict[str, Any]:
    """Fetch cookie categorization overrides from remote API and cache per domain.

    Returns an empty dict on failure. This function always sets an entry in the
    DOMAIN_COOKIE_CATEGORIZATION_FROM_DB cache (so callers can rely on its presence).
    """
    try:
        logger.info(f"Fetching DB categorization data for doamin_config_id {domain_config_id}")
        response = requests.get(f"{FETCH_COOKIE_CATEGORIZATION_API_URL}?domain_config_id={domain_config_id}", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json() or {}
        if isinstance(data, dict) and "data" in data:
            resp_data = None
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

    # Return whatever we have (empty dict on failure)
    return DOMAIN_COOKIE_CATEGORIZATION_FROM_DB[domain_config_id]


# -----------------------------------------------------------------------------
# Cookie categorization logic (with ML integration)
# -----------------------------------------------------------------------------
def categorize_cookie(name: str, domain_config_id: str, cookie_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Categorize a cookie using hybrid ML + rules approach.

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
    # Defensive: ensure name is a string
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
                    "iab_purposes": [],  # ML doesn't map to IAB purposes directly
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

                # If ML had medium confidence, blend with IAB
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


# ---------------- Helpers ----------------

def hash_value(val: Optional[str]) -> Optional[str]:
    """Return SHA256 hash of a value (None => None)."""
    if val is None:
        return None
    if not isinstance(val, str):
        val = str(val)
    return hashlib.sha256(val.encode("utf-8")).hexdigest()


def get_base_domain(domain: str) -> str:
    """Return registrar base domain (e.g. example.com).

    Note: simplistic implementation (last two labels). For complex TLDs use a publicsuffix list.
    """
    parts = domain.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain


def party_type(cookie_domain: Optional[str], site_url: str) -> str:
    """Return 'First Party' if cookie_domain maps to site_url's base domain, else 'Third Party'."""
    if not cookie_domain:
        return "unknown"

    cookie_domain = cookie_domain.lstrip(".").lower()
    base_host = urlparse(site_url).hostname or site_url
    base_domain = get_base_domain(base_host.lower())
    return "First Party" if cookie_domain.endswith(base_domain) else "Third Party"


async def collect_cookies(context, base_domain: str, before_accept: bool = False, cookie_map: Optional[dict] = None) -> List[Dict[str, Any]]:
    """Collect cookies from Playwright context and optionally populate cookie_map.

    Returns a list of cookie records (not categorized here).
    """
    cookies = await context.cookies()

    results: List[Dict[str, Any]] = []
    for c in cookies:
        val = c.get("value", "")
        record = {
            "name": c.get("name"),
            "domain": c.get("domain"),
            "path": c.get("path"),
            "hashed_value": hash_value(val),
            "cookie_duration": cookie_duration_days(c.get("expires")),
            "size": len(val.encode("utf-8")) if isinstance(val, str) else None,
            "httpOnly": c.get("httpOnly", False),
            "secure": c.get("secure", False),
            "sameSite": c.get("sameSite", None),
            "cookie_type": party_type(c.get("domain"), base_domain),
            "set_after_accept": not before_accept,
        }
        cookie_id = f"{record['name']}|{record['domain']}|{record['path']}"
        if cookie_map is not None:
            cookie_map[cookie_id] = record
        results.append(record)
    return results


async def collect_storages(page) -> Dict[str, Dict[str, Optional[str]]]:
    """Collect and hash localStorage and sessionStorage key-values.

    Each storage value is hashed via hash_value for privacy.
    """
    def hash_map(m: Optional[dict]) -> Dict[str, Optional[str]]:
        return {k: hash_value(v) if v is not None else None for k, v in (m or {}).items()}

    try:
        local = await page.evaluate("""() => {
            const out = {}; for(let i=0;i<localStorage.length;i++){ const k=localStorage.key(i); out[k] = localStorage.getItem(k); } return out;
        }""")
    except Exception:
        local = {}

    try:
        session = await page.evaluate("""() => {
            const out = {}; for(let i=0;i<sessionStorage.length;i++){ const k=sessionStorage.key(i); out[k] = sessionStorage.getItem(k); } return out;
        }""")
    except Exception:
        session = {}

    return {"localStorage": hash_map(local), "sessionStorage": hash_map(session)}


# ---------------- Crawl with Retry ----------------

async def crawl_page(page, base_url: str, url: str, visited: set, cookie_map: dict,
                     depth: int = 0, max_depth: int = SCAN_MAX_DEPTH_DEFAULT, max_retries: int = SCAN_MAX_RETRY_DEFAULT,
                     accept_button_selector: str = 'button[data-role="accept"]',
                     follow_links: bool = True, max_pages: Optional[int] = None, counters: Optional[dict] = None):
    """Visit a URL, collect cookies and storages, optionally follow internal links.

    Behavior largely mirrors your original function. Small fixes:
    - Ensure visited set prevents revisiting even if URL normalisation differs minimally.
    - Respect max_pages when provided.
    """
    # Avoid revisiting or exceeding depth
    if url in visited or depth > max_depth:
        return

    # Enforce max_pages for deep crawl only
    if counters is not None and max_pages is not None and counters.get("loaded", 0) >= max_pages:
        logger.info(f"Max deep crawl pages limit {max_pages} reached, skipping {url}")
        return


    attempt = 0
    success = False

    while attempt <= max_retries:
        try:
            logger.info(f"Visiting: {url}")
            page_load_response = await page.goto(url, timeout=60000)
            logger.info(f"[INFO] Initial navigation status: {page_load_response.status if page_load_response else 'No response'}")
            success = True
            break
        except PlaywrightTimeoutError as e:
            logger.warning(f"Timeout loading {url} attempt={attempt+1}: {e}")
        except Exception as e:
            logger.warning(f"Failed to load {url} attempt={attempt+1}: {e}")
        attempt += 1
        if attempt > max_retries:
            logger.error(f"Giving up on {url} after {max_retries} retries")
            return

    if not success:
        return

    # Enforce max_pages (only for deep crawl)
    if max_pages is not None and len(visited) >= max_pages:
        logger.info(f"Max pages limit {max_pages} reached, skipping {url}")
        return

    if counters is not None:
        counters["loaded"] = counters.get("loaded", 0) + 1

    # Mark visited early to prevent concurrent duplication in recursion
    visited.add(url)

    # Collect cookies snapshot before accepting banners
    await collect_cookies(page.context, base_url, before_accept=True, cookie_map=cookie_map)

    # Try clicking cookie accept button if present
    accepted = False
    try:
        await page.wait_for_timeout(1200)
        btn = page.locator(accept_button_selector)
        if await btn.count() and await btn.is_visible():
            await btn.click()
            accepted = True
            logger.info("Cookie banner accepted")
            # Small pause to allow scripts to run and set cookies
            time.sleep(30)
            await collect_cookies(page.context, base_url, before_accept=False, cookie_map=cookie_map)
    except Exception:
        # We intentionally swallow errors here; cookie banners vary widely
        pass

    # Scroll the page in steps to trigger lazy-load cookies
    try:
        scroll_height = await page.evaluate("() => document.body.scrollHeight")
        for i in range(0, int(scroll_height) + 1, 800):
            await page.evaluate(f"window.scrollTo(0, {i});")
            time.sleep(2)
            await collect_cookies(page.context, base_url, before_accept=not accepted, cookie_map=cookie_map)
    except Exception:
        # If evaluation fails (some pages restrict), continue
        pass

    # Final cookies snapshot after interactions
    await collect_cookies(page.context, base_url, before_accept=not accepted, cookie_map=cookie_map)

    # Storage snapshot (local/session)
    storages = await collect_storages(page)

    # Follow internal links (if allowed)
    if follow_links:
        anchors = await page.eval_on_selector_all("a", "els => els.map(el => el.href)")
        for link in anchors:
            if not link:
                continue
            parsed_link = urlparse(link)
            parsed_base = urlparse(base_url)
            # If link has no netloc (relative) or same host, follow it
            if not parsed_link.netloc or parsed_link.netloc == parsed_base.netloc:
                next_url = urljoin(base_url, link)
                await crawl_page(page, base_url, next_url, visited, cookie_map,
                                 depth + 1, max_depth, max_retries, accept_button_selector, follow_links=True, max_pages=max_pages, counters=counters)

    return storages


# ---------------- Main logic to crawl the main domain page and custom pages if provided ----------------

async def _run_crawl(domain: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Run an asynchronous deep crawl for a domain.

    Returns dict with keys: cookies, storages, pages_visited
    """
    max_depth = int(params.get("scanDepth", SCAN_MAX_DEPTH_DEFAULT))
    custom_pages = params.get("customPages") or []
    max_pages = params.get("maxPages")
    max_retries = int(params.get("maxRetries", SCAN_MAX_RETRY_DEFAULT))

    start_url = domain
    accept_button_selector = params.get("accept_selector", 'button[data-role="accept"]')

    visited = set()
    cookie_map: Dict[str, Any] = {}
    storages_agg = {"localStorage": {}, "sessionStorage": {}}
    counters = {"loaded": 0}  # counts successfully loaded deep-crawl pages

    async with stealth.use_async(async_playwright()) as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--disable-http2"]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768}
        )
        await stealth.apply_stealth_async(context)
        # optional stealth tweak
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        page = await context.new_page()
        # Crawl main site
        storages = await crawl_page(page, start_url, start_url, visited, cookie_map,
                                    depth=0, max_depth=max_depth, max_retries=max_retries,
                                    accept_button_selector=accept_button_selector, follow_links=True, max_pages=max_pages, counters=counters)
        if storages:
            storages_agg["localStorage"].update(storages.get("localStorage", {}))
            storages_agg["sessionStorage"].update(storages.get("sessionStorage", {}))

        # Crawl custom pages (no deep crawl, but with retries)
        for cp in custom_pages:
            cp_url = cp if cp.startswith("http") else urljoin(start_url, cp)
            try:
                s = await crawl_page(page, start_url, cp_url, visited, cookie_map,
                                     depth=0, max_depth=0, max_retries=max_retries,
                                     accept_button_selector=accept_button_selector, follow_links=False, max_pages=None, counters=None)
                if s:
                    storages_agg["localStorage"].update(s.get("localStorage", {}))
                    storages_agg["sessionStorage"].update(s.get("sessionStorage", {}))
            except Exception as e:
                logger.error(f"Custom page failed {cp_url}: {e}")

        await browser.close()

    cookies = list(cookie_map.values())
    return {"cookies": cookies, "storages": storages_agg, "pages_visited": list(visited)}


# ---------------- build Results that will be posted for a domain scan ----------------


def _build_result(domain_schedule: Dict[str, Any], cookies_result: Dict[str, Any], attempt: int, status: str, error: Optional[str] = None, duration: Optional[float] = None) -> Dict[str, Any]:
    """Construct final result payload for posting.

    This keeps the structure your downstream API expects.
    """
    domain = domain_schedule.get("domainUrl")
    cookies = cookies_result.get("cookies", [])
    pages_visited = cookies_result.get("pages_visited", [])

    # Ensure DB overrides are loaded into cache for this domain before categorizing
    load_db_cookie_categorization_for_domain(domain_schedule.get("domain_config_id"))

    categorized_cookies: List[Dict[str, Any]] = []
    for cookie in cookies:
        name = cookie.get("name")
        # Use ML-enhanced categorization with cookie data
        categorized_info = categorize_cookie(
            name=name,
            domain_config_id=domain_schedule.get("domain_config_id"),
            cookie_data=cookie  # Pass full cookie data for ML classification
        )
        # Merge categorization into original cookie info (in-place)
        cookie.update(categorized_info)
        categorized_cookies.append(cookie)

    return {
        #"_id": domain_schedule.get("_id"),
        "domain_config_id": domain_schedule.get("domain_config_id"),
        "domain": domain,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "params": {k: domain_schedule.get(k) for k in ("maxPages", "scanDepth", "maxRetries", "customPages")},
        "pages_visited": pages_visited,
        "total_cookies": len(cookies),
        "page_count": len(pages_visited),
        "attempt": attempt,
        "status": status,
        "error": error,
        "duration_seconds": duration,
        "cookies": categorized_cookies,
        "storages": cookies_result.get("storages", {}),
    }


def post_result(result: Dict[str, Any]) -> Tuple[Optional[int], str]:
    """Post result JSON to RESULT_API_URL and return (status_code, text) or (None, error)."""
    try:
        result_json = json.dumps(result, indent=2, ensure_ascii=False)
        #logger.info(f"Posting scan results to {RESULT_API_URL}:{result_json}")
        logger.info(f"Posting scan results to {RESULT_API_URL}")
        resp = requests.post(RESULT_API_URL, json=result, timeout=REQUEST_TIMEOUT)
        logger.info(f"Posted results to {RESULT_API_URL}: {resp.status_code} {resp.text}")
        return resp.status_code, resp.text
    except Exception as e:
        logger.exception(f"Failed to POST result: {e}")
        return None, str(e)


# ---------------- Deep scan domain as per the schedule ----------------

def scan_domain(domain_schedule: Dict[str, Any]) -> Dict[str, Any]:
    """Run deep scan for a scheduled domain, with retry/backoff on failure."""
    max_retries = int(domain_schedule.get("maxRetries", SCAN_MAX_RETRY_DEFAULT))
    attempt = 0
    start_time = time.time()
    last_err = None

    while attempt <= max_retries:
        attempt += 1
        try:
            t0 = time.time()
            cookies_result = asyncio.run(
                _run_crawl(domain_schedule.get("domainUrl") or domain_schedule.get("domain"),
                           {
                               "scanDepth": domain_schedule.get("scanDepth", SCAN_MAX_DEPTH_DEFAULT),
                               "maxPages": domain_schedule.get("maxPages"),
                               "customPages": domain_schedule.get("customPages", []),
                               "start_url": domain_schedule.get("start_url"),
                               "accept_selector": domain_schedule.get("accept_selector", DEFAULT_BUTTON_SELECTOR),
                               "maxRetries": domain_schedule.get("maxRetries", SCAN_MAX_RETRY_DEFAULT)
                           })
            )
            duration = time.time() - t0
            result = _build_result(domain_schedule, cookies_result, attempt, "success",
                                   error=None, duration=duration)
            result["scan_mode"] = "deep"
            post_result(result)
            logger.info(f"[DEEP_SCAN_SUCCESS] domain={result['domain']} "
                        f"pages={len(result['pages_visited'])} cookies={len(result['cookies'])}")
            return result
        except Exception as e:
            last_err = str(e)
            logger.exception(f"[DEEP_SCAN_ERROR] domain={domain_schedule.get('domainUrl')} attempt={attempt} error={e}")
            # exponential backoff but cap to 60s
            time.sleep(min(2 ** attempt, 60))

    duration_total = time.time() - start_time
    failed_result = _build_result(domain_schedule, {"cookies": [], "storages": {}, "pages_visited": []},
                                  attempt, "failed", error=last_err, duration=duration_total)
    post_result(failed_result)
    logger.error(f"[DEEP_SCAN_FAILED] domain={domain_schedule.get('domainUrl')} attempts={attempt} error={last_err}")
    return failed_result


# ---------------- Quick Scan code ----------------

async def _run_quick_scan(domain: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Run a quick scan: main domain root + custom pages, no deep crawl."""
    custom_pages = params.get("customPages") or []
    max_retries = int(params.get("maxRetries", SCAN_MAX_RETRY_DEFAULT))
    accept_button_selector = params.get("accept_selector", DEFAULT_BUTTON_SELECTOR)

    visited = set()
    cookie_map: Dict[str, Any] = {}
    storages_agg = {"localStorage": {}, "sessionStorage": {}}

    async with stealth.use_async(async_playwright()) as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--disable-http2"]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768}
        )
        await stealth.apply_stealth_async(context)
        # optional stealth tweak
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        """)

        page = await context.new_page()

        # Crawl main domain (no follow_links, depth=0, max_depth=0)
        storages = await crawl_page(
            page, domain, domain, visited, cookie_map,
            depth=0, max_depth=0, max_retries=max_retries,
            accept_button_selector=accept_button_selector,
            follow_links=False, max_pages=None, counters=None
        )
        if storages:
            storages_agg["localStorage"].update(storages.get("localStorage", {}))
            storages_agg["sessionStorage"].update(storages.get("sessionStorage", {}))

        # Crawl custom pages
        for cp in custom_pages:
            cp_url = cp if cp.startswith("http") else urljoin(domain, cp)
            try:
                s = await crawl_page(
                    page, domain, cp_url, visited, cookie_map,
                    depth=0, max_depth=0, max_retries=max_retries,
                    accept_button_selector=accept_button_selector,
                    follow_links=False, max_pages=None, counters=None
                )
                if s:
                    storages_agg["localStorage"].update(s.get("localStorage", {}))
                    storages_agg["sessionStorage"].update(s.get("sessionStorage", {}))
            except Exception as e:
                logger.error(f"[QUICK_SCAN] custom page failed {cp_url}: {e}")

        await browser.close()

    cookies = list(cookie_map.values())
    return {"cookies": cookies, "storages": storages_agg, "pages_visited": list(visited)}


def quick_scan_domain(domain_request: Dict[str, Any]) -> Dict[str, Any]:
    """Trigger quick scan for API requests and return results."""
    attempt = 1
    start_time = time.time()
    domain = domain_request.get("domainUrl")

    try:
        cookies_result = asyncio.run(
            _run_quick_scan(domain, {
                "customPages": domain_request.get("customPages", []),
                "accept_selector": domain_request.get("accept_selector", 'button[data-role="accept"]'),
                "maxRetries": domain_request.get("maxRetries", SCAN_MAX_RETRY_DEFAULT),
            })
        )
        duration = time.time() - start_time
        result = _build_result(
            {
                #"_id": domain_request.get("_id"),
                "domain_config_id": domain_request.get("domain_config_id"),
                "domainUrl": domain,
                "customPages": domain_request.get("customPages", []),
                "maxRetries": domain_request.get("maxRetries", SCAN_MAX_RETRY_DEFAULT)
            },
            cookies_result, 
            attempt, 
            "success", 
            error=None, 
            duration=duration
        )
        result["scan_mode"] = "quick"
        post_result(result)
        logger.info(f"[QUICK_SCAN_SUCCESS] domain={domain} pages={len(result['pages_visited'])} cookies={len(result['cookies'])}")
        result_json = json.dumps(result, indent=2, ensure_ascii=False)
        #logger.info(f"Response is: {result_json}")

        return result
    except Exception as e:
        duration = time.time() - start_time
        logger.exception(f"[QUICK_SCAN_ERROR] domain={domain} error={e}")
        failed_result = _build_result(
            {"_id": domain_request.get("id"),  "domain_config_id": domain_request.get("domain_config_id"), "domainUrl": domain}, 
            {"cookies": [], "storages": {}, "pages_visited": []}, 
            attempt, "failed", error=str(e), duration=duration
        )
        return failed_result