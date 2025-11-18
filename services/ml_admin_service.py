"""
ML Admin Service

Business logic for ML model administration, review queue, and feedback collection.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID, uuid4
import logging

from ml_classifier.config import (
    MODEL_FILE,
    METADATA_FILE,
    TRAINING_DATA_DIR,
    HIGH_CONFIDENCE_THRESHOLD,
)

logger = logging.getLogger(__name__)


class MLAdminService:
    """
    Service for ML model administration and feedback collection.

    Provides functionality for:
    - ML model metrics and statistics
    - Low-confidence cookie review queue
    - Admin feedback/corrections
    - Training queue management
    """

    def __init__(self, db_pool=None, redis_client=None):
        """
        Initialize ML admin service.

        Args:
            db_pool: Database connection pool (optional for now)
            redis_client: Redis client for caching (optional for now)
        """
        self.db_pool = db_pool
        self.redis_client = redis_client
        self.feedback_file = TRAINING_DATA_DIR / "admin_feedback.csv"

        # Ensure training data directory exists
        TRAINING_DATA_DIR.mkdir(exist_ok=True)

    async def get_model_metrics(self) -> Dict[str, Any]:
        """
        Get ML model performance metrics.

        Returns:
            Dict with model metrics and statistics
        """
        # Load model metadata
        model_info = self._load_model_metadata()

        # Get prediction statistics (would come from database in production)
        # For now, return mock data with model info
        metrics = {
            "model_version": model_info.get("model_version", "unknown"),
            "model_type": model_info.get("model_type", "unknown"),
            "trained_date": model_info.get("trained_date"),
            "accuracy": model_info.get("metrics", {}).get("accuracy"),
            "predictions_count": 0,  # Would query from scan_results.cookies table
            "predictions_today": 0,
            "avg_confidence": 0.55,  # Would calculate from recent scans
            "confidence_distribution": {
                "high": 0,  # ≥75%
                "medium": 0,  # 50-75%
                "low": 0,  # <50%
            },
            "category_distribution": {
                "Necessary": 0,
                "Functional": 0,
                "Analytics": 0,
                "Advertising": 0,
            },
            "source_distribution": {
                "ML_High": 0,
                "ML_Low": 0,
                "IAB_ML_Blend": 0,
                "Rules_ML_Agree": 0,
                "IAB": 0,
                "RulesJSON": 0,
                "DB": 0,
                "Fallback": 0,
            },
            "low_confidence_count": 0,  # requires_review=true
            "feedback_count": self._count_feedback(),
            "last_feedback_date": self._get_last_feedback_date(),
        }

        # If database is available, fetch real statistics
        if self.db_pool:
            try:
                real_metrics = await self._fetch_database_metrics()
                metrics.update(real_metrics)
            except Exception as e:
                logger.warning(f"Could not fetch database metrics: {e}")

        return metrics

    async def get_low_confidence_cookies(
        self,
        limit: int = 100,
        offset: int = 0,
        min_confidence: float = 0.0,
        max_confidence: float = 0.75,
        category: Optional[str] = None,
        review_status: str = "pending"
    ) -> List[Dict[str, Any]]:
        """
        Get cookies with low ML confidence for manual review.

        Args:
            limit: Maximum cookies to return
            offset: Offset for pagination
            min_confidence: Minimum confidence threshold
            max_confidence: Maximum confidence threshold
            category: Filter by predicted category
            review_status: Review status filter

        Returns:
            List of low-confidence cookies
        """
        # In production, query from database:
        # SELECT * FROM cookies
        # WHERE ml_confidence BETWEEN min_confidence AND max_confidence
        #   AND requires_review = true
        #   AND review_status = ?
        # ORDER BY ml_confidence ASC, created_at DESC
        # LIMIT ? OFFSET ?

        # For now, return mock data structure
        cookies = []

        # If database available, fetch real data
        if self.db_pool:
            try:
                cookies = await self._fetch_low_confidence_from_db(
                    limit, offset, min_confidence, max_confidence, category, review_status
                )
            except Exception as e:
                logger.warning(f"Could not fetch from database: {e}")

        return cookies

    async def submit_feedback(
        self,
        feedback: Any,  # FeedbackRequest model
        admin_user_id: UUID
    ) -> Dict[str, Any]:
        """
        Submit admin correction for ML prediction.

        Args:
            feedback: Feedback request model
            admin_user_id: Admin user ID

        Returns:
            Dict with feedback_id and status
        """
        feedback_id = uuid4()

        # Prepare feedback record
        feedback_record = {
            "feedback_id": str(feedback_id),
            "admin_user_id": str(admin_user_id),
            "cookie_id": str(feedback.cookie_id) if feedback.cookie_id else None,
            "scan_id": str(feedback.scan_id) if feedback.scan_id else None,
            "cookie_name": feedback.cookie_name,
            "cookie_domain": feedback.cookie_domain,
            "predicted_category": feedback.predicted_category,
            "correct_category": feedback.correct_category,
            "ml_confidence": feedback.ml_confidence,
            "notes": feedback.notes,
            "created_at": datetime.utcnow().isoformat(),
            "review_status": "approved",  # Auto-approve admin corrections
        }

        # Store in database (if available)
        if self.db_pool:
            try:
                await self._store_feedback_in_db(feedback_record)
            except Exception as e:
                logger.error(f"Failed to store feedback in database: {e}")

        # Append to CSV for training
        added_to_queue = self._append_feedback_to_csv(feedback_record)

        return {
            "feedback_id": feedback_id,
            "message": "Feedback submitted successfully",
            "added_to_training_queue": added_to_queue,
        }

    async def submit_bulk_feedback(
        self,
        corrections: List[Any],
        admin_user_id: UUID
    ) -> Dict[str, Any]:
        """
        Submit multiple corrections at once.

        Args:
            corrections: List of FeedbackRequest models
            admin_user_id: Admin user ID

        Returns:
            Dict with submission statistics
        """
        results = {
            "total": len(corrections),
            "success": 0,
            "failed": 0,
            "errors": []
        }

        for correction in corrections:
            try:
                await self.submit_feedback(correction, admin_user_id)
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "cookie_name": correction.cookie_name,
                    "error": str(e)
                })

        return results

    async def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current ML model.

        Returns:
            Dict with model information
        """
        metadata = self._load_model_metadata()

        # Get model file size
        model_size_mb = None
        if MODEL_FILE.exists():
            model_size_mb = MODEL_FILE.stat().st_size / (1024 * 1024)  # Convert to MB

        return {
            "model_version": metadata.get("model_version", "unknown"),
            "model_type": metadata.get("model_type", "unknown"),
            "trained_date": metadata.get("trained_date"),
            "categories": metadata.get("categories", []),
            "feature_count": metadata.get("feature_count", 0),
            "accuracy": metadata.get("metrics", {}).get("accuracy"),
            "f1_score": metadata.get("metrics", {}).get("f1_macro"),
            "model_file": str(MODEL_FILE),
            "model_size_mb": round(model_size_mb, 2) if model_size_mb else None,
        }

    async def update_review_status(
        self,
        feedback_id: UUID,
        new_status: str,
        admin_user_id: UUID
    ) -> Dict[str, Any]:
        """
        Update review status of a feedback record.

        Args:
            feedback_id: Feedback record ID
            new_status: New review status
            admin_user_id: Admin user ID

        Returns:
            Dict with update confirmation
        """
        allowed_statuses = ["pending", "reviewed", "approved", "rejected"]
        if new_status not in allowed_statuses:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(allowed_statuses)}")

        # Update in database (if available)
        if self.db_pool:
            try:
                await self._update_feedback_status_in_db(feedback_id, new_status, admin_user_id)
            except Exception as e:
                logger.error(f"Failed to update status in database: {e}")
                raise

        return {
            "feedback_id": str(feedback_id),
            "status": new_status,
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": str(admin_user_id),
        }

    async def get_training_queue_status(self) -> Dict[str, Any]:
        """
        Get status of corrections queued for retraining.

        Returns:
            Dict with training queue statistics
        """
        feedback_count = self._count_feedback()

        # Count by category (if CSV exists)
        category_counts = {}
        if self.feedback_file.exists():
            try:
                import csv
                with open(self.feedback_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        cat = row.get("correct_category", "Unknown")
                        category_counts[cat] = category_counts.get(cat, 0) + 1
            except Exception as e:
                logger.warning(f"Could not parse feedback CSV: {e}")

        return {
            "total_corrections": feedback_count,
            "corrections_by_category": category_counts,
            "last_training_date": self._get_last_training_date(),
            "feedback_file": str(self.feedback_file),
            "ready_for_retraining": feedback_count >= 100,  # Threshold for retraining
        }

    # Private helper methods

    def _load_model_metadata(self) -> Dict[str, Any]:
        """Load model metadata from JSON file."""
        if not METADATA_FILE.exists():
            return {}

        try:
            with open(METADATA_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load model metadata: {e}")
            return {}

    def _count_feedback(self) -> int:
        """Count total feedback records in CSV."""
        if not self.feedback_file.exists():
            return 0

        try:
            with open(self.feedback_file, 'r') as f:
                return sum(1 for line in f) - 1  # Subtract header
        except Exception:
            return 0

    def _get_last_feedback_date(self) -> Optional[str]:
        """Get date of last feedback submission."""
        if not self.feedback_file.exists():
            return None

        try:
            import csv
            with open(self.feedback_file, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                if rows:
                    last_row = rows[-1]
                    return last_row.get("created_at")
        except Exception:
            pass

        return None

    def _get_last_training_date(self) -> Optional[str]:
        """Get date of last model training."""
        metadata = self._load_model_metadata()
        return metadata.get("trained_date")

    def _append_feedback_to_csv(self, feedback_record: Dict[str, Any]) -> bool:
        """Append feedback to CSV file for training."""
        try:
            import csv

            # Check if file exists to determine if we need header
            file_exists = self.feedback_file.exists()

            with open(self.feedback_file, 'a', newline='') as f:
                fieldnames = [
                    "feedback_id", "admin_user_id", "cookie_id", "scan_id",
                    "cookie_name", "cookie_domain", "predicted_category",
                    "correct_category", "ml_confidence", "notes",
                    "created_at", "review_status"
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)

                # Write header if new file
                if not file_exists:
                    writer.writeheader()

                writer.writerow(feedback_record)

            logger.info(f"Feedback appended to {self.feedback_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to append feedback to CSV: {e}")
            return False

    async def _fetch_database_metrics(self) -> Dict[str, Any]:
        """Fetch real metrics from database (placeholder for future implementation)."""
        # TODO: Implement database queries
        # Example:
        # async with self.db_pool.acquire() as conn:
        #     total = await conn.fetchval("SELECT COUNT(*) FROM cookies WHERE ml_confidence IS NOT NULL")
        #     ...
        return {}

    async def _fetch_low_confidence_from_db(
        self, limit, offset, min_conf, max_conf, category, status
    ) -> List[Dict[str, Any]]:
        """Fetch low-confidence cookies from database (placeholder)."""
        # TODO: Implement database query
        return []

    async def _store_feedback_in_db(self, feedback_record: Dict[str, Any]):
        """Store feedback in database (placeholder)."""
        # TODO: Implement database insert
        pass

    async def _update_feedback_status_in_db(self, feedback_id, new_status, admin_user_id):
        """Update feedback status in database (placeholder)."""
        # TODO: Implement database update
        pass
