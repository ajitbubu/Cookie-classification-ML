"""
Scan-related data models.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, validator, UUID4


class ScanStatus(str, Enum):
    """Scan status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanMode(str, Enum):
    """Scan mode enumeration."""
    QUICK = "quick"
    DEEP = "deep"
    SCHEDULED = "scheduled"
    REALTIME = "realtime"


class CookieType(str, Enum):
    """Cookie type enumeration."""
    FIRST_PARTY = "First Party"
    THIRD_PARTY = "Third Party"
    UNKNOWN = "unknown"


class Cookie(BaseModel):
    """Cookie data model with ML classification support."""
    cookie_id: Optional[UUID4] = None
    scan_id: Optional[UUID4] = None
    name: str = Field(..., description="Cookie name")
    domain: str = Field(..., description="Cookie domain")
    path: str = Field(default="/", description="Cookie path")
    hashed_value: Optional[str] = Field(None, description="SHA-256 hashed cookie value")
    cookie_duration: Optional[str] = Field(None, description="Cookie duration (e.g., '30 days', 'Session')")
    size: Optional[int] = Field(None, description="Cookie size in bytes")
    http_only: bool = Field(default=False, description="HttpOnly flag")
    secure: bool = Field(default=False, description="Secure flag")
    same_site: Optional[str] = Field(None, description="SameSite attribute")
    category: Optional[str] = Field(None, description="Cookie category (Necessary, Functional, Analytics, Advertising)")
    vendor: Optional[str] = Field(None, description="Cookie vendor/provider")
    cookie_type: Optional[CookieType] = Field(None, description="First Party or Third Party")
    set_after_accept: bool = Field(default=False, description="Whether cookie was set after accepting banner")
    iab_purposes: List[int] = Field(default_factory=list, description="IAB purpose IDs")
    description: Optional[str] = Field(None, description="Cookie description")
    source: Optional[str] = Field(
        None,
        description="Categorization source (DB, ML_High, ML_Low, IAB, IAB_ML_Blend, RulesJSON, Rules_ML_Agree, Fallback)"
    )

    # ML Classification Fields
    ml_confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="ML classification confidence score (0.0-1.0)"
    )
    ml_probabilities: Optional[Dict[str, float]] = Field(
        None,
        description="ML probability distribution across all categories"
    )
    classification_evidence: Optional[List[str]] = Field(
        None,
        description="List of evidence/reasoning for the classification"
    )
    requires_review: bool = Field(
        default=False,
        description="Whether this cookie requires manual review (low ML confidence)"
    )

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: Optional[datetime] = None

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ScanParams(BaseModel):
    """Scan parameters model."""
    max_pages: Optional[int] = Field(None, description="Maximum pages to scan (deep scan only)")
    scan_depth: int = Field(default=5, ge=0, le=10, description="Maximum crawl depth")
    max_retries: int = Field(default=3, ge=0, le=5, description="Maximum retry attempts")
    custom_pages: List[str] = Field(default_factory=list, description="Custom pages to scan")
    accept_selector: str = Field(
        default='button[data-role="accept"]',
        description="CSS selector for cookie accept button"
    )
    wait_for_dynamic_content: int = Field(
        default=5,
        ge=5,
        le=60,
        description="Seconds to wait for dynamic content (5-60)"
    )
    wait_strategy: str = Field(
        default="timeout",
        description="Wait strategy: timeout, networkidle, domcontentloaded, load, combined"
    )
    follow_external_links: bool = Field(default=False, description="Whether to follow external links")
    collect_screenshots: bool = Field(default=False, description="Whether to collect screenshots")
    user_agent: Optional[str] = Field(None, description="Custom user agent")
    viewport: Dict[str, int] = Field(
        default_factory=lambda: {"width": 1366, "height": 768},
        description="Browser viewport dimensions"
    )
    
    @validator('custom_pages')
    def validate_custom_pages(cls, v):
        """Validate custom pages list."""
        if v and len(v) > 50:
            raise ValueError("Maximum 50 custom pages allowed")
        return v
    
    @validator('wait_strategy')
    def validate_wait_strategy(cls, v):
        """Validate wait strategy."""
        valid_strategies = ['timeout', 'networkidle', 'domcontentloaded', 'load', 'combined']
        if v.lower() not in valid_strategies:
            raise ValueError(f"wait_strategy must be one of: {', '.join(valid_strategies)}")
        return v.lower()


class ScanResult(BaseModel):
    """Scan result data model."""
    scan_id: Optional[UUID4] = None
    domain_config_id: UUID4 = Field(..., description="Domain configuration ID")
    domain: str = Field(..., description="Scanned domain")
    scan_mode: ScanMode = Field(..., description="Scan mode used")
    timestamp_utc: datetime = Field(default_factory=datetime.utcnow, description="Scan timestamp")
    status: ScanStatus = Field(..., description="Scan status")
    duration_seconds: Optional[float] = Field(None, ge=0, description="Scan duration in seconds")
    total_cookies: int = Field(default=0, ge=0, description="Total cookies found")
    page_count: int = Field(default=0, ge=0, description="Number of pages visited")
    error: Optional[str] = Field(None, description="Error message if scan failed")
    params: ScanParams = Field(default_factory=ScanParams, description="Scan parameters")
    pages_visited: List[str] = Field(default_factory=list, description="List of visited URLs")
    cookies: List[Cookie] = Field(default_factory=list, description="Collected cookies")
    storages: Dict[str, Dict[str, str]] = Field(
        default_factory=lambda: {"localStorage": {}, "sessionStorage": {}},
        description="Storage data (localStorage, sessionStorage)"
    )
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    @validator('cookies', pre=True)
    def validate_cookies(cls, v):
        """Ensure cookies is a list."""
        if v is None:
            return []
        return v
    
    @validator('total_cookies', always=True)
    def sync_total_cookies(cls, v, values):
        """Sync total_cookies with cookies list length."""
        if 'cookies' in values:
            return len(values['cookies'])
        return v


class ScanProgress(BaseModel):
    """Real-time scan progress model."""
    scan_id: UUID4
    status: ScanStatus
    current_page: Optional[str] = None
    pages_visited: int = 0
    cookies_found: int = 0
    progress_percentage: float = Field(ge=0, le=100)
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
