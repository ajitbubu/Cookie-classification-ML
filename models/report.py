"""
Report-related data models.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, UUID4


class ReportType(str, Enum):
    """Report type enumeration."""
    COMPLIANCE = "compliance"
    COMPARISON = "comparison"
    TREND = "trend"
    CUSTOM = "custom"


class ReportFormat(str, Enum):
    """Report format enumeration."""
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    CSV = "csv"


class Report(BaseModel):
    """Report data model."""
    report_id: Optional[UUID4] = None
    scan_id: Optional[UUID4] = Field(None, description="Associated scan ID")
    report_type: ReportType = Field(..., description="Type of report")
    format: ReportFormat = Field(..., description="Report format")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Generation timestamp")
    data: Dict[str, Any] = Field(default_factory=dict, description="Report data")
    file_path: Optional[str] = Field(None, description="Path to generated report file")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    created_by: Optional[UUID4] = Field(None, description="User who created the report")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ComplianceMetrics(BaseModel):
    """Compliance metrics model."""
    total_cookies: int = Field(ge=0, description="Total number of cookies")
    cookies_by_category: Dict[str, int] = Field(
        default_factory=dict,
        description="Cookie count by category"
    )
    cookies_by_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Cookie count by type (First/Third Party)"
    )
    compliance_score: float = Field(ge=0, le=100, description="Compliance score (0-100)")
    third_party_ratio: float = Field(ge=0, le=1, description="Ratio of third-party cookies")
    cookies_set_after_accept: int = Field(ge=0, description="Cookies set after banner acceptance")
    cookies_set_before_accept: int = Field(ge=0, description="Cookies set before banner acceptance")


class TrendData(BaseModel):
    """Trend analysis data model."""
    domain: str = Field(..., description="Domain analyzed")
    metric: str = Field(..., description="Metric name")
    time_range: Dict[str, datetime] = Field(..., description="Time range (start, end)")
    data_points: list = Field(default_factory=list, description="Time series data points")
    trend_direction: str = Field(..., description="Trend direction (increasing, decreasing, stable)")
    change_percentage: Optional[float] = Field(None, description="Percentage change over period")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class Anomaly(BaseModel):
    """Anomaly detection model."""
    anomaly_id: Optional[UUID4] = None
    scan_id: UUID4 = Field(..., description="Scan where anomaly was detected")
    domain: str = Field(..., description="Domain")
    detected_at: datetime = Field(default_factory=datetime.utcnow, description="Detection timestamp")
    anomaly_type: str = Field(..., description="Type of anomaly")
    metric: str = Field(..., description="Affected metric")
    current_value: float = Field(..., description="Current value")
    expected_value: float = Field(..., description="Expected value")
    deviation_percentage: float = Field(..., description="Deviation percentage")
    severity: str = Field(..., description="Severity level (low, medium, high)")
    description: str = Field(..., description="Anomaly description")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
