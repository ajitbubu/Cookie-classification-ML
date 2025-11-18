"""
ML-based Cookie Classification Module

This module provides machine learning-powered cookie classification
without relying on external LLM APIs. Uses scikit-learn Random Forest
for auto-categorization with confidence scoring.

Components:
- FeatureExtractor: Extract ML features from cookie objects
- ModelTrainer: Training pipeline for Random Forest classifier
- Classifier: Inference engine with confidence scoring
- ConfidenceScorer: Evidence generation and explainability
- FallbackStrategy: Hybrid ML + rules approach
"""

__version__ = "1.0.0"

from .feature_extractor import FeatureExtractor
from .classifier import MLCookieClassifier

__all__ = [
    "FeatureExtractor",
    "MLCookieClassifier",
]
