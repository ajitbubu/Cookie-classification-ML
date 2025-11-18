import os

# Default API endpoint for fetching domain schedules
#DEFAULT_API_URL = "http://127.0.0.1:9010/api/schedules"
DEFAULT_API_URL = "http://172.174.5.76:8880/idredact_enterprise_onprem_mw/get_cookie_scheduler_info"

# Result POST endpoint (Flask will expose this)
#DEFAULT_RESULT_API_URL = "http://127.0.0.1:9010/api/results"
DEFAULT_RESULT_API_URL = "http://172.174.5.76:8880/idredact_enterprise_onprem_mw/save_domain_scan_result"

# Default API endpoint for fetching domain cookie categorisation
#DEFAULT_FETCH_COOKIE_CATEGORIZATION_API_URL = "http://127.0.01:9010/api/fetch-domain-cookie-categorization"
DEFAULT_FETCH_COOKIE_CATEGORIZATION_API_URL = "http://172.174.5.76:8880/idredact_enterprise_onprem_mw/get_domain_cookie_categorization"

# Default scheduler refresh interval in seconds
DEFAULT_REFRESH_INTERVAL = 300

# Default request timeout for API calls (seconds)
DEFAULT_REQUEST_TIMEOUT = 10

# Maximum concurrent scans for thread pool
DEFAULT_MAX_WORKERS = 5

# Logging directory
DEFAULT_LOG_DIR = "logs"
LOG_DIR = os.environ.get("LOG_DIR", DEFAULT_LOG_DIR)
LOG_FILE = os.path.join(LOG_DIR, "dynamic_cookie_scanning.log")
LOG_TO_CONSOLE = os.getenv("LOG_TO_CONSOLE", "true").lower() == "true"

# Actual values used by scheduler, overridden by environment variables if set
API_URL = os.environ.get("API_URL", DEFAULT_API_URL)
RESULT_API_URL = os.environ.get("RESULT_API_URL", DEFAULT_RESULT_API_URL)
FETCH_COOKIE_CATEGORIZATION_API_URL = os.environ.get("FETCH_COOKIE_CATEGORIZATION_API_URL", DEFAULT_FETCH_COOKIE_CATEGORIZATION_API_URL)

REFRESH_INTERVAL = int(os.environ.get("REFRESH_INTERVAL", DEFAULT_REFRESH_INTERVAL))
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", DEFAULT_REQUEST_TIMEOUT))
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", DEFAULT_MAX_WORKERS))


# Job scheduling options
JOB_REPLACE_EXISTING_INSTANCE = os.getenv("JOB_REPLACE_EXISTING_INSTANCE", "True") 
JOB_MAX_INSTANCES = int(os.getenv("JOB_MAX_INSTANCES", 1))
JOB_COALESCE = os.getenv("JOB_COALESCE", "true").lower() == "true"
JOB_MISFIRE_GRACE_TIME = int(os.getenv("JOB_MISFIRE_GRACE_TIME", 300))

# scan default options
SCAN_MAX_DEPTH_DEFAULT = 5
SCAN_MAX_RETRY_DEFAULT = 3

# Mapping layer between IAB Purposes and CMP categories. DSG team can verify them
IAB_PURPOSE_CATEGORY_MAP = {
    1: "Necessary",      # Storage and access of information
    2: "Necessary",      # Basic ads
    3: "Functional",     # Personalization
    4: "Advertising",    # Ad selection, delivery, reporting
    5: "Advertising",    # Content selection, delivery, reporting
    6: "Analytics",      # Measurement
    7: "Analytics",      # Market research
    8: "Functional",     # Product development
    9: "Functional",     # Security, fraud prevention
    10: "Analytics"      # Match data with offline sources
}

# IAB file for vendor -> purpose -> cookie category mapping 
IAB_GVL_URL = "https://vendor-list.consensu.org/v3/vendor-list.json"

# Priority order: Necessary > Functional > Analytics > Advertising
CATEGORY_PRIORITY = ["Necessary", "Functional", "Analytics", "Advertising"]

DEFAULT_BUTTON_SELECTOR='button[data-role="accept"]'