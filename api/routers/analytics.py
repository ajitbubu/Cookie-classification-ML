"""
Analytics endpoints for reports, trends, and metrics.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request, status
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, UUID4

from api.auth.dependencies import get_current_user, require_scope
from models.user import TokenData
from models.report import ReportFormat, Report, TrendData
from services.analytics_service import AnalyticsService

router = APIRouter()


def get_analytics_service(request: Request) -> AnalyticsService:
    """Dependency to get analytics service from app state."""
    return AnalyticsService(request.app.state.db_pool, request.app.state.redis_client)


# Request/Response models
class GenerateReportRequest(BaseModel):
    """Request model for generating custom reports."""
    scan_id: UUID4 = Field(..., description="Scan ID to generate report for")
    format: ReportFormat = Field(default=ReportFormat.JSON, description="Report format")


class TrendRequest(BaseModel):
    """Request model for trend analysis."""
    domain: str = Field(..., description="Domain to analyze")
    metric: str = Field(default='total_cookies', description="Metric to analyze")
    days: int = Field(default=30, ge=1, le=365, description="Number of days to look back")


@router.get(
    "/reports/{scan_id}",
    response_model=Report,
    status_code=status.HTTP_200_OK,
    summary="Get report for scan",
    description="Retrieve an existing report or generate a new one for a scan"
)
async def get_report(
    scan_id: UUID4,
    format: ReportFormat = Query(default=ReportFormat.JSON, description="Report format"),
    current_user: TokenData = Depends(require_scope("analytics:read")),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get or generate a compliance report for a scan.
    
    If a report in the requested format already exists, it will be returned.
    Otherwise, a new report will be generated.
    
    **Required scope**: `analytics:read`
    """
    try:
        # Generate report (in production, check if report exists first)
        report = await analytics_service.generate_report(scan_id, format)
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )


@router.post(
    "/reports",
    response_model=Report,
    status_code=status.HTTP_201_CREATED,
    summary="Generate custom report",
    description="Generate a new compliance report for a scan"
)
async def generate_custom_report(
    request: GenerateReportRequest,
    current_user: TokenData = Depends(require_scope("analytics:write")),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Generate a custom compliance report.
    
    Creates a new report for the specified scan in the requested format.
    Supports PDF, HTML, and JSON formats.
    
    **Required scope**: `analytics:write`
    """
    try:
        report = await analytics_service.generate_report(
            request.scan_id,
            request.format
        )
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )


@router.get(
    "/trends",
    response_model=TrendData,
    status_code=status.HTTP_200_OK,
    summary="Get trend data",
    description="Get historical trend data for a domain and metric"
)
async def get_trends(
    domain: str = Query(..., description="Domain to analyze"),
    metric: str = Query(default='total_cookies', description="Metric to analyze"),
    days: int = Query(default=30, ge=1, le=365, description="Number of days to look back"),
    current_user: TokenData = Depends(require_scope("analytics:read")),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get trend data for a domain.
    
    Analyzes historical scan data to identify trends in the specified metric.
    Supported metrics:
    - total_cookies
    - compliance_score
    - third_party_ratio
    - first_party_ratio
    - cookies_after_consent
    - cookies_before_consent
    
    **Required scope**: `analytics:read`
    """
    try:
        trend_data = await analytics_service.get_trend_data(
            domain=domain,
            metric=metric,
            days=days
        )
        return trend_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trend data: {str(e)}"
        )


@router.get(
    "/metrics",
    status_code=status.HTTP_200_OK,
    summary="Get metrics summary",
    description="Get aggregated metrics summary for recent scans"
)
async def get_metrics_summary(
    domain: Optional[str] = Query(default=None, description="Optional domain filter"),
    days: int = Query(default=7, ge=1, le=365, description="Number of days to look back"),
    current_user: TokenData = Depends(require_scope("analytics:read")),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get metrics summary for recent scans.
    
    Returns aggregated metrics including:
    - Total scans
    - Domains scanned
    - Total cookies found
    - Average compliance score
    - Average scan duration
    - Cookie distribution by category
    
    **Required scope**: `analytics:read`
    """
    try:
        metrics = await analytics_service.get_metrics_summary(
            domain=domain,
            days=days
        )
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics summary: {str(e)}"
        )
