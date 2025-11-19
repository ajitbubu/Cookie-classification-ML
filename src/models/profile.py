"""
Scan profile data models.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field, validator, UUID4


class ScanMode(str, Enum):
    """Scan mode enumeration."""
    QUICK = "quick"
    DEEP = "deep"
    SCHEDULED = "scheduled"
    REALTIME = "realtime"


class ScanProfile(BaseModel):
    """Scan profile data model."""
    profile_id: Optional[UUID4] = None
    name: str = Field(..., min_length=1, max_length=255, description="Profile name")
    scan_mode: ScanMode = Field(..., description="Scan mode")
    config: Dict[str, Any] = Field(default_factory=dict, description="Profile configuration")
    created_by: Optional[UUID4] = Field(None, description="User who created the profile")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Configuration fields (stored in config dict but exposed as properties)
    max_depth: int = Field(default=5, ge=0, le=10, description="Maximum crawl depth")
    max_pages: Optional[int] = Field(None, ge=1, le=1000, description="Maximum pages to scan")
    max_retries: int = Field(default=3, ge=0, le=5, description="Maximum retry attempts")
    custom_pages: List[str] = Field(default_factory=list, description="Custom pages to scan")
    accept_button_selector: str = Field(
        default='button[data-role="accept"]',
        description="CSS selector for cookie accept button"
    )
    wait_for_dynamic_content: int = Field(
        default=5,
        ge=0,
        le=60,
        description="Seconds to wait for dynamic content"
    )
    follow_external_links: bool = Field(default=False, description="Whether to follow external links")
    collect_screenshots: bool = Field(default=False, description="Whether to collect screenshots")
    user_agent: Optional[str] = Field(None, description="Custom user agent")
    viewport: Dict[str, int] = Field(
        default_factory=lambda: {"width": 1366, "height": 768},
        description="Browser viewport dimensions"
    )
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    @validator('custom_pages')
    def validate_custom_pages(cls, v):
        """Validate custom pages list."""
        if v and len(v) > 50:
            raise ValueError("Maximum 50 custom pages allowed")
        return v
    
    @validator('viewport')
    def validate_viewport(cls, v):
        """Validate viewport dimensions."""
        if 'width' not in v or 'height' not in v:
            raise ValueError("Viewport must have 'width' and 'height' keys")
        if v['width'] < 320 or v['width'] > 3840:
            raise ValueError("Viewport width must be between 320 and 3840")
        if v['height'] < 240 or v['height'] > 2160:
            raise ValueError("Viewport height must be between 240 and 2160")
        return v
    
    def dict(self, *args, **kwargs):
        """Override dict to merge config fields."""
        d = super().dict(*args, **kwargs)
        # Merge configuration fields into config dict
        config_fields = {
            'max_depth', 'max_pages', 'max_retries', 'custom_pages',
            'accept_button_selector', 'wait_for_dynamic_content',
            'follow_external_links', 'collect_screenshots',
            'user_agent', 'viewport'
        }
        d['config'] = {k: d.pop(k) for k in config_fields if k in d}
        return d


class ScanProfileCreate(BaseModel):
    """Scan profile creation model."""
    name: str = Field(..., min_length=1, max_length=255, description="Profile name")
    scan_mode: ScanMode = Field(..., description="Scan mode")
    max_depth: int = Field(default=5, ge=0, le=10)
    max_pages: Optional[int] = Field(None, ge=1, le=1000)
    max_retries: int = Field(default=3, ge=0, le=5)
    custom_pages: List[str] = Field(default_factory=list)
    accept_button_selector: str = Field(default='button[data-role="accept"]')
    wait_for_dynamic_content: int = Field(default=5, ge=0, le=60)
    follow_external_links: bool = Field(default=False)
    collect_screenshots: bool = Field(default=False)
    user_agent: Optional[str] = None
    viewport: Dict[str, int] = Field(default_factory=lambda: {"width": 1366, "height": 768})
    
    class Config:
        use_enum_values = True


class ScanProfileUpdate(BaseModel):
    """Scan profile update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    scan_mode: Optional[ScanMode] = None
    max_depth: Optional[int] = Field(None, ge=0, le=10)
    max_pages: Optional[int] = Field(None, ge=1, le=1000)
    max_retries: Optional[int] = Field(None, ge=0, le=5)
    custom_pages: Optional[List[str]] = None
    accept_button_selector: Optional[str] = None
    wait_for_dynamic_content: Optional[int] = Field(None, ge=0, le=60)
    follow_external_links: Optional[bool] = None
    collect_screenshots: Optional[bool] = None
    user_agent: Optional[str] = None
    viewport: Optional[Dict[str, int]] = None
    
    class Config:
        use_enum_values = True
