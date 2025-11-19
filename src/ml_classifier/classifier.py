"""
ML Cookie Classifier - Inference Engine

Production-ready classifier for categorizing cookies using trained ML model.
Provides confidence scoring, evidence generation, and batch processing.
"""

from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import joblib
import numpy as np
import pandas as pd

from .config import (
    MODEL_FILE,
    SCALER_FILE,
    LABEL_ENCODER_FILE,
    METADATA_FILE,
    HIGH_CONFIDENCE_THRESHOLD,
    MEDIUM_CONFIDENCE_THRESHOLD,
    LOW_CONFIDENCE_THRESHOLD,
)
from .feature_extractor import FeatureExtractor


@dataclass
class ClassificationResult:
    """
    Result of cookie classification.

    Attributes:
        category: Predicted category (Necessary, Functional, Analytics, Advertising)
        confidence: Confidence score (0.0-1.0)
        probabilities: Probability distribution across all categories
        source: Classification source (e.g., "ML_Model_v1.0")
        evidence: List of evidence points explaining the prediction
        requires_review: Whether manual review is recommended
    """

    category: str
    confidence: float
    probabilities: Dict[str, float]
    source: str
    evidence: List[str]
    requires_review: bool = False


class MLCookieClassifier:
    """
    ML-powered cookie classifier.

    Features:
    - Fast inference (<1ms per cookie)
    - Confidence scoring for all predictions
    - Evidence generation for explainability
    - Batch processing for performance
    - Fallback recommendations for low-confidence predictions
    """

    def __init__(self, model_path: Optional[Path] = None):
        """
        Initialize classifier with trained model.

        Args:
            model_path: Path to trained model file (defaults to config)

        Raises:
            FileNotFoundError: If model files not found
        """
        self.model_path = model_path or MODEL_FILE
        self.feature_extractor = FeatureExtractor()

        # Load model artifacts
        self._load_model()

    def _load_model(self) -> None:
        """Load trained model and preprocessing artifacts."""
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model not found: {self.model_path}\n"
                f"Train a model first with: python scripts/train_model.py"
            )

        self.model = joblib.load(self.model_path)
        self.scaler = joblib.load(SCALER_FILE)
        self.label_encoder = joblib.load(LABEL_ENCODER_FILE)

        # Load metadata
        if METADATA_FILE.exists():
            import json

            with open(METADATA_FILE) as f:
                self.metadata = json.load(f)
                self.model_version = self.metadata.get("model_version", "unknown")
        else:
            self.metadata = {}
            self.model_version = "unknown"

    def classify(self, cookie: Dict[str, Any]) -> ClassificationResult:
        """
        Classify a single cookie.

        Args:
            cookie: Cookie dictionary with fields:
                - name: str
                - domain: str
                - path: str (optional)
                - cookie_duration: str
                - httpOnly: bool (optional)
                - secure: bool (optional)
                - sameSite: str (optional)
                - cookie_type: str (optional)
                - size: int (optional)
                - set_after_accept: bool (optional)

        Returns:
            ClassificationResult with category, confidence, and evidence
        """
        # Extract features
        features = self.feature_extractor.extract(cookie)
        features_df = pd.DataFrame([features])

        # Scale features
        features_scaled = self.scaler.transform(features_df)

        # Predict with probabilities
        probabilities = self.model.predict_proba(features_scaled)[0]
        predicted_class_idx = np.argmax(probabilities)
        predicted_class = self.label_encoder.classes_[predicted_class_idx]
        confidence = probabilities[predicted_class_idx]

        # Create probability distribution
        prob_dict = {
            category: float(prob)
            for category, prob in zip(self.label_encoder.classes_, probabilities)
        }

        # Generate evidence
        evidence = self._generate_evidence(cookie, features, predicted_class, confidence)

        # Determine if review is needed
        requires_review = confidence < MEDIUM_CONFIDENCE_THRESHOLD

        return ClassificationResult(
            category=predicted_class,
            confidence=float(confidence),
            probabilities=prob_dict,
            source=f"ML_Model_v{self.model_version}",
            evidence=evidence,
            requires_review=requires_review,
        )

    def classify_batch(self, cookies: List[Dict[str, Any]]) -> List[ClassificationResult]:
        """
        Classify multiple cookies efficiently.

        Args:
            cookies: List of cookie dictionaries

        Returns:
            List of ClassificationResults
        """
        if not cookies:
            return []

        # Extract features for all cookies
        features_df = self.feature_extractor.extract_batch(cookies)

        # Scale features
        features_scaled = self.scaler.transform(features_df)

        # Batch prediction
        probabilities_batch = self.model.predict_proba(features_scaled)

        # Build results
        results = []
        for i, (cookie, probabilities) in enumerate(zip(cookies, probabilities_batch)):
            predicted_class_idx = np.argmax(probabilities)
            predicted_class = self.label_encoder.classes_[predicted_class_idx]
            confidence = probabilities[predicted_class_idx]

            prob_dict = {
                category: float(prob)
                for category, prob in zip(self.label_encoder.classes_, probabilities)
            }

            # Get features for this cookie
            features = features_df.iloc[i].to_dict()
            evidence = self._generate_evidence(cookie, features, predicted_class, confidence)

            results.append(
                ClassificationResult(
                    category=predicted_class,
                    confidence=float(confidence),
                    probabilities=prob_dict,
                    source=f"ML_Model_v{self.model_version}",
                    evidence=evidence,
                    requires_review=confidence < MEDIUM_CONFIDENCE_THRESHOLD,
                )
            )

        return results

    def _generate_evidence(
        self,
        cookie: Dict[str, Any],
        features: Dict[str, Any],
        predicted_category: str,
        confidence: float,
    ) -> List[str]:
        """
        Generate human-readable evidence for the classification.

        Args:
            cookie: Original cookie dictionary
            features: Extracted features
            predicted_category: Predicted category
            confidence: Confidence score

        Returns:
            List of evidence strings
        """
        evidence = []
        name = cookie.get("name", "")
        domain = cookie.get("domain", "")

        # Top feature contributions
        if hasattr(self.model, "feature_importances_"):
            # Get top 3 features by importance
            feature_importance = self.model.feature_importances_
            feature_names = list(features.keys())

            top_indices = np.argsort(feature_importance)[-3:][::-1]
            for idx in top_indices:
                feature_name = feature_names[idx]
                importance = feature_importance[idx]
                if importance > 0.05:  # Only show significant features
                    evidence.append(
                        f"Feature '{feature_name}' has {importance:.1%} model influence"
                    )

        # Category-specific evidence
        if predicted_category == "Necessary":
            if features.get("is_session"):
                evidence.append("Session cookie suggests essential functionality")
            if features.get("matches_necessary_pattern"):
                evidence.append(f"Cookie name '{name}' matches known necessary pattern")
            if features.get("httpOnly"):
                evidence.append("HttpOnly flag indicates security cookie")
            if not features.get("is_third_party"):
                evidence.append("First-party cookie typical for necessary functions")

        elif predicted_category == "Functional":
            if features.get("matches_functional_pattern"):
                evidence.append(f"Cookie name '{name}' matches functional pattern (language, theme, etc.)")
            if not features.get("is_third_party"):
                evidence.append("First-party cookie suggests site preferences")
            duration_days = features.get("duration_days", 0)
            if 30 <= duration_days <= 365:
                evidence.append(f"Duration '{duration_days} days' typical for user preferences")

        elif predicted_category == "Analytics":
            if features.get("matches_analytics_pattern"):
                evidence.append(f"Cookie name '{name}' matches known analytics pattern")
            if features.get("is_known_analytics"):
                evidence.append(f"Domain '{domain}' is recognized analytics vendor")
            if features.get("is_third_party"):
                evidence.append("Third-party cookie common for analytics tracking")
            if features.get("set_after_accept"):
                evidence.append("Set after consent acceptance (typical for analytics)")

        elif predicted_category == "Advertising":
            if features.get("matches_advertising_pattern"):
                evidence.append(f"Cookie name '{name}' matches advertising pattern")
            if features.get("is_known_advertising"):
                evidence.append(f"Domain '{domain}' is recognized advertising vendor")
            if features.get("is_third_party"):
                evidence.append("Third-party cookie typical for ad tracking")
            duration_days = features.get("duration_days", 0)
            if duration_days >= 90:
                evidence.append(f"Long duration '{duration_days} days' common for ad retargeting")

        # Confidence-based evidence
        if confidence >= HIGH_CONFIDENCE_THRESHOLD:
            evidence.append(f"High confidence prediction ({confidence:.1%})")
        elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
            evidence.append(f"Medium confidence prediction ({confidence:.1%}) - consider blending with rules")
        else:
            evidence.append(f"Low confidence prediction ({confidence:.1%}) - manual review recommended")

        # Limit to top 5 evidence points
        return evidence[:5]

    def get_confidence_level(self, confidence: float) -> str:
        """
        Get human-readable confidence level.

        Args:
            confidence: Confidence score (0.0-1.0)

        Returns:
            Confidence level string
        """
        if confidence >= HIGH_CONFIDENCE_THRESHOLD:
            return "High"
        elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
            return "Medium"
        else:
            return "Low"

    def get_fallback_recommendation(self, result: ClassificationResult) -> Dict[str, Any]:
        """
        Get recommendation for fallback strategy if confidence is low.

        Args:
            result: Classification result

        Returns:
            Fallback recommendation dictionary
        """
        if result.confidence >= HIGH_CONFIDENCE_THRESHOLD:
            return {
                "use_ml_prediction": True,
                "fallback_to": None,
                "reason": "High confidence ML prediction",
            }
        elif result.confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
            return {
                "use_ml_prediction": True,
                "fallback_to": "blend_with_rules",
                "reason": "Medium confidence - blend ML with rules for safety",
            }
        else:
            # Low confidence - recommend fallback
            # Sort probabilities to find alternatives
            sorted_probs = sorted(
                result.probabilities.items(), key=lambda x: x[1], reverse=True
            )

            return {
                "use_ml_prediction": False,
                "fallback_to": "rules_or_iab",
                "reason": f"Low confidence ({result.confidence:.1%}) - use fallback",
                "alternative_categories": sorted_probs[:2],  # Top 2 alternatives
                "flag_for_review": True,
            }

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.

        Returns:
            Model metadata dictionary
        """
        return {
            "model_version": self.model_version,
            "model_type": type(self.model).__name__,
            "categories": list(self.label_encoder.classes_),
            "feature_count": len(self.feature_extractor.get_feature_names()),
            "metadata": self.metadata,
        }


def demo_classification():
    """Demo function to test classifier with example cookies."""
    print("=" * 60)
    print("ML COOKIE CLASSIFIER DEMO")
    print("=" * 60)

    # Initialize classifier
    try:
        classifier = MLCookieClassifier()
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        print("\nPlease train the model first:")
        print("  python scripts/train_model.py")
        return

    # Show model info
    info = classifier.get_model_info()
    print(f"\nModel Version: {info['model_version']}")
    print(f"Categories: {', '.join(info['categories'])}")

    # Test cookies
    test_cookies = [
        {
            "name": "_ga",
            "domain": ".google-analytics.com",
            "cookie_duration": "730 days",
            "cookie_type": "Third Party",
            "httpOnly": False,
            "secure": True,
            "sameSite": "None",
        },
        {
            "name": "sessionid",
            "domain": ".example.com",
            "cookie_duration": "Session",
            "cookie_type": "First Party",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Strict",
        },
        {
            "name": "_fbp",
            "domain": ".facebook.com",
            "cookie_duration": "90 days",
            "cookie_type": "Third Party",
            "httpOnly": False,
            "secure": True,
            "sameSite": "None",
            "set_after_accept": True,
        },
        {
            "name": "language",
            "domain": ".example.com",
            "cookie_duration": "365 days",
            "cookie_type": "First Party",
            "httpOnly": False,
            "secure": True,
            "sameSite": "Lax",
        },
    ]

    print("\n" + "=" * 60)
    print("CLASSIFICATION RESULTS")
    print("=" * 60)

    for cookie in test_cookies:
        result = classifier.classify(cookie)

        print(f"\nCookie: {cookie['name']}")
        print(f"  Domain: {cookie['domain']}")
        print(f"  Category: {result.category} ({result.confidence:.1%} confidence)")
        print(f"  Confidence Level: {classifier.get_confidence_level(result.confidence)}")
        print(f"  Evidence:")
        for evidence in result.evidence:
            print(f"    - {evidence}")

        # Show fallback recommendation
        fallback = classifier.get_fallback_recommendation(result)
        if fallback.get("fallback_to"):
            print(f"  Recommendation: {fallback['reason']}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    demo_classification()
