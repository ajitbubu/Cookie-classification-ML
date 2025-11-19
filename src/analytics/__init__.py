"""
Analytics module for Cookie Scanner Platform.

This module provides analytics capabilities including:
- Metrics calculation (compliance scores, distributions)
- Report generation (PDF, HTML, JSON)
- Trend analysis
- Anomaly detection
- Comparison reports
"""

from .metrics_calculator import MetricsCalculator
from .report_generator import ReportGenerator
from .trend_analyzer import TrendAnalyzer
from .anomaly_detector import AnomalyDetector
from .comparison_generator import ComparisonGenerator
from .cache_manager import AnalyticsCacheManager

__all__ = [
    'MetricsCalculator',
    'ReportGenerator',
    'TrendAnalyzer',
    'AnomalyDetector',
    'ComparisonGenerator',
    'AnalyticsCacheManager',
]
