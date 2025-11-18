"""
ML Admin endpoints for model management, review queue, and feedback.

Provides API endpoints for:
- ML model metrics and performance
- Low-confidence cookie review queue
- Admin feedback/corrections for model improvement
- Model information and statistics
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request, status
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, UUID4, validator
from uuid import UUID

from api.auth.dependencies import get_current_user, require_scope
from models.user import TokenData
from services.ml_admin_service import MLAdminService

router = APIRouter()


def get_ml_admin_service(request: Request) -> MLAdminService:
    """Dependency to get ML admin service from app state."""
    return MLAdminService(request.app.state.db_pool, request.app.state.redis_client)


# Request/Response models
class MLMetricsResponse(BaseModel):
    """ML model metrics response."""
    model_version: str = Field(..., description="Current model version")
    model_type: str = Field(..., description="Model type (e.g., RandomForestClassifier)")
    trained_date: Optional[str] = Field(None, description="Last training date (ISO format)")
    accuracy: Optional[float] = Field(None, description="Model test accuracy")
    predictions_count: int = Field(..., description="Total predictions made")
    predictions_today: int = Field(..., description="Predictions made today")
    avg_confidence: float = Field(..., description="Average confidence score")
    confidence_distribution: Dict[str, int] = Field(
        ...,
        description="Distribution by confidence level (high, medium, low)"
    )
    category_distribution: Dict[str, int] = Field(
        ...,
        description="Distribution by predicted category"
    )
    source_distribution: Dict[str, int] = Field(
        ...,
        description="Distribution by classification source"
    )
    low_confidence_count: int = Field(..., description="Cookies needing review")
    feedback_count: int = Field(..., description="Admin corrections submitted")
    last_feedback_date: Optional[str] = Field(None, description="Last feedback submission date")


class LowConfidenceCookie(BaseModel):
    """Cookie requiring manual review."""
    cookie_id: Optional[UUID4] = Field(None, description="Cookie database ID")
    scan_id: Optional[UUID4] = Field(None, description="Scan ID")
    name: str = Field(..., description="Cookie name")
    domain: str = Field(..., description="Cookie domain")
    predicted_category: str = Field(..., description="ML predicted category")
    ml_confidence: float = Field(..., description="ML confidence score (0-1)")
    ml_probabilities: Dict[str, float] = Field(..., description="Category probabilities")
    classification_evidence: List[str] = Field(..., description="Evidence/reasoning")
    cookie_type: Optional[str] = Field(None, description="First Party or Third Party")
    cookie_duration: Optional[str] = Field(None, description="Cookie duration")
    set_after_accept: bool = Field(default=False, description="Set after consent")
    created_at: Optional[datetime] = Field(None, description="Scan date")
    review_status: str = Field(default="pending", description="Review status")


class FeedbackRequest(BaseModel):
    """Admin feedback/correction request."""
    cookie_id: Optional[UUID4] = Field(None, description="Cookie database ID (if available)")
    scan_id: Optional[UUID4] = Field(None, description="Scan ID")
    cookie_name: str = Field(..., description="Cookie name")
    cookie_domain: str = Field(..., description="Cookie domain")
    correct_category: str = Field(..., description="Correct category")
    predicted_category: str = Field(..., description="ML predicted category")
    ml_confidence: Optional[float] = Field(None, description="ML confidence")
    notes: Optional[str] = Field(None, description="Admin notes")

    @validator('correct_category')
    def validate_category(cls, v):
        """Validate category is one of the allowed values."""
        allowed = ["Necessary", "Functional", "Analytics", "Advertising"]
        if v not in allowed:
            raise ValueError(f"Category must be one of: {', '.join(allowed)}")
        return v


class FeedbackResponse(BaseModel):
    """Feedback submission response."""
    feedback_id: UUID4 = Field(..., description="Feedback record ID")
    message: str = Field(..., description="Success message")
    added_to_training_queue: bool = Field(..., description="Whether added to training queue")


class ModelInfoResponse(BaseModel):
    """ML model information response."""
    model_version: str
    model_type: str
    trained_date: Optional[str]
    categories: List[str]
    feature_count: int
    accuracy: Optional[float]
    f1_score: Optional[float]
    model_file: str
    model_size_mb: Optional[float]


class BulkFeedbackRequest(BaseModel):
    """Bulk feedback submission."""
    corrections: List[FeedbackRequest] = Field(..., description="List of corrections")

    @validator('corrections')
    def validate_corrections(cls, v):
        """Validate corrections list."""
        if len(v) > 100:
            raise ValueError("Maximum 100 corrections per bulk request")
        if len(v) == 0:
            raise ValueError("At least one correction required")
        return v


# Endpoints

@router.get(
    "/metrics",
    response_model=MLMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get ML model metrics",
    description="Retrieve ML model performance metrics and statistics"
)
async def get_ml_metrics(
    current_user: TokenData = Depends(require_scope("ml:read")),
    ml_service: MLAdminService = Depends(get_ml_admin_service)
):
    """
    Get ML model performance metrics and statistics.

    Returns comprehensive metrics including:
    - Model version and metadata
    - Prediction counts and confidence distribution
    - Low-confidence cookies needing review
    - Admin feedback statistics

    **Required scope**: `ml:read`
    """
    try:
        metrics = await ml_service.get_model_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve ML metrics: {str(e)}"
        )


@router.get(
    "/low-confidence",
    response_model=List[LowConfidenceCookie],
    status_code=status.HTTP_200_OK,
    summary="Get low-confidence cookies",
    description="Retrieve cookies with low ML confidence requiring manual review"
)
async def get_low_confidence_cookies(
    limit: int = Query(default=100, ge=1, le=500, description="Maximum cookies to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    max_confidence: float = Query(default=0.75, ge=0.0, le=1.0, description="Maximum confidence threshold"),
    category: Optional[str] = Query(None, description="Filter by predicted category"),
    review_status: str = Query(default="pending", description="Review status filter"),
    current_user: TokenData = Depends(require_scope("ml:read")),
    ml_service: MLAdminService = Depends(get_ml_admin_service)
):
    """
    Get cookies with low ML confidence for manual review.

    Returns cookies that:
    - Have ML confidence below specified threshold (default: <75%)
    - Are flagged with `requires_review: true`
    - Have not been reviewed yet (or match review_status filter)

    Use pagination with `limit` and `offset` for large result sets.

    **Required scope**: `ml:read`
    """
    try:
        cookies = await ml_service.get_low_confidence_cookies(
            limit=limit,
            offset=offset,
            min_confidence=min_confidence,
            max_confidence=max_confidence,
            category=category,
            review_status=review_status
        )
        return cookies
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve low-confidence cookies: {str(e)}"
        )


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit admin feedback",
    description="Submit correction for ML prediction to improve model"
)
async def submit_feedback(
    feedback: FeedbackRequest,
    current_user: TokenData = Depends(require_scope("ml:write")),
    ml_service: MLAdminService = Depends(get_ml_admin_service)
):
    """
    Submit admin correction for ML prediction.

    The feedback will be:
    - Stored in the database with admin ID and timestamp
    - Added to training queue for next model retraining
    - Used to calculate model accuracy over time

    **Required scope**: `ml:write`
    """
    try:
        result = await ml_service.submit_feedback(
            feedback=feedback,
            admin_user_id=current_user.user_id
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.post(
    "/feedback/bulk",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Submit bulk feedback",
    description="Submit multiple corrections at once (max 100)"
)
async def submit_bulk_feedback(
    bulk_feedback: BulkFeedbackRequest,
    current_user: TokenData = Depends(require_scope("ml:write")),
    ml_service: MLAdminService = Depends(get_ml_admin_service)
):
    """
    Submit multiple admin corrections at once.

    Useful for batch labeling sessions. Maximum 100 corrections per request.

    Returns:
    - Total submitted count
    - Success count
    - Failed count (with error details)

    **Required scope**: `ml:write`
    """
    try:
        result = await ml_service.submit_bulk_feedback(
            corrections=bulk_feedback.corrections,
            admin_user_id=current_user.user_id
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit bulk feedback: {str(e)}"
        )


@router.get(
    "/model-info",
    response_model=ModelInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get model information",
    description="Retrieve information about the current ML model"
)
async def get_model_info(
    current_user: TokenData = Depends(require_scope("ml:read")),
    ml_service: MLAdminService = Depends(get_ml_admin_service)
):
    """
    Get information about the current ML model.

    Returns model metadata including:
    - Version and type
    - Training date
    - Categories and feature count
    - Performance metrics

    **Required scope**: `ml:read`
    """
    try:
        info = await ml_service.get_model_info()
        return info
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ML model not found. Train a model first."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve model info: {str(e)}"
        )


@router.put(
    "/feedback/{feedback_id}/review-status",
    status_code=status.HTTP_200_OK,
    summary="Update review status",
    description="Update review status of a low-confidence cookie"
)
async def update_review_status(
    feedback_id: UUID4,
    status_update: str = Query(..., description="New status: pending, reviewed, approved, rejected"),
    current_user: TokenData = Depends(require_scope("ml:write")),
    ml_service: MLAdminService = Depends(get_ml_admin_service)
):
    """
    Update review status of a low-confidence cookie.

    Statuses:
    - `pending`: Awaiting review
    - `reviewed`: Admin has reviewed
    - `approved`: Correction approved for training
    - `rejected`: Correction rejected

    **Required scope**: `ml:write`
    """
    try:
        result = await ml_service.update_review_status(
            feedback_id=feedback_id,
            new_status=status_update,
            admin_user_id=current_user.user_id
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update status: {str(e)}"
        )


@router.get(
    "/training-queue",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get training queue status",
    description="Get status of corrections queued for model retraining"
)
async def get_training_queue_status(
    current_user: TokenData = Depends(require_scope("ml:read")),
    ml_service: MLAdminService = Depends(get_ml_admin_service)
):
    """
    Get status of corrections queued for next model retraining.

    Returns:
    - Total corrections in queue
    - Breakdown by category
    - Last training date
    - Estimated next training date

    **Required scope**: `ml:read`
    """
    try:
        status_info = await ml_service.get_training_queue_status()
        return status_info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get training queue status: {str(e)}"
        )
