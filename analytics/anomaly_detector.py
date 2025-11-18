"""
Anomaly detector for cookie compliance monitoring.

Detects anomalies by comparing current scans with historical baselines:
- Significant changes in cookie counts (>20% threshold)
- New cookie categories appearing
- Unusual third-party cookie ratios
- Compliance score drops
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import statistics
from uuid import uuid4

from models.scan import ScanResult
from models.report import Anomaly
from analytics.metrics_calculator import MetricsCalculator

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detect anomalies in cookie scan data."""
    
    # Default threshold for anomaly detection (20% as per requirements)
    DEFAULT_THRESHOLD = 20.0
    
    # Severity thresholds
    SEVERITY_THRESHOLDS = {
        'low': 20.0,      # 20-40% deviation
        'medium': 40.0,   # 40-60% deviation
        'high': 60.0      # >60% deviation
    }
    
    def __init__(
        self,
        threshold: float = DEFAULT_THRESHOLD,
        metrics_calculator: Optional[MetricsCalculator] = None
    ):
        """
        Initialize anomaly detector.
        
        Args:
            threshold: Percentage threshold for anomaly detection
            metrics_calculator: Metrics calculator instance (creates new if None)
        """
        self.threshold = threshold
        self.metrics_calculator = metrics_calculator or MetricsCalculator()
        logger.info(f"AnomalyDetector initialized with threshold: {threshold}%")
    
    def detect_anomalies(
        self,
        current_scan: ScanResult,
        historical_scans: List[ScanResult],
        min_history: int = 3
    ) -> List[Anomaly]:
        """
        Detect anomalies by comparing current scan with historical baseline.
        
        Args:
            current_scan: Current scan result to check
            historical_scans: List of historical scan results for baseline
            min_history: Minimum number of historical scans required
            
        Returns:
            List of detected anomalies
        """
        if len(historical_scans) < min_history:
            logger.warning(
                f"Insufficient historical data for anomaly detection "
                f"(need {min_history}, have {len(historical_scans)})"
            )
            return []
        
        logger.info(
            f"Detecting anomalies for scan {current_scan.scan_id} "
            f"using {len(historical_scans)} historical scans"
        )
        
        anomalies = []
        
        # Detect total cookie count anomalies
        cookie_count_anomaly = self._detect_cookie_count_anomaly(
            current_scan, historical_scans
        )
        if cookie_count_anomaly:
            anomalies.append(cookie_count_anomaly)
        
        # Detect compliance score anomalies
        compliance_anomaly = self._detect_compliance_score_anomaly(
            current_scan, historical_scans
        )
        if compliance_anomaly:
            anomalies.append(compliance_anomaly)
        
        # Detect third-party ratio anomalies
        third_party_anomaly = self._detect_third_party_ratio_anomaly(
            current_scan, historical_scans
        )
        if third_party_anomaly:
            anomalies.append(third_party_anomaly)
        
        # Detect category distribution anomalies
        category_anomalies = self._detect_category_anomalies(
            current_scan, historical_scans
        )
        anomalies.extend(category_anomalies)
        
        # Detect new categories
        new_category_anomalies = self._detect_new_categories(
            current_scan, historical_scans
        )
        anomalies.extend(new_category_anomalies)
        
        logger.info(
            f"Anomaly detection complete: {len(anomalies)} anomalies detected"
        )
        
        return anomalies
    
    def _detect_cookie_count_anomaly(
        self,
        current_scan: ScanResult,
        historical_scans: List[ScanResult]
    ) -> Optional[Anomaly]:
        """Detect anomalies in total cookie count."""
        current_count = len(current_scan.cookies)
        historical_counts = [len(scan.cookies) for scan in historical_scans]
        
        # Calculate baseline (average)
        baseline = statistics.mean(historical_counts)
        
        if baseline == 0:
            return None
        
        # Calculate deviation
        deviation_percentage = abs((current_count - baseline) / baseline * 100)
        
        if deviation_percentage >= self.threshold:
            severity = self._calculate_severity(deviation_percentage)
            
            anomaly = Anomaly(
                anomaly_id=uuid4(),
                scan_id=current_scan.scan_id,
                domain=current_scan.domain,
                detected_at=datetime.utcnow(),
                anomaly_type='cookie_count_change',
                metric='total_cookies',
                current_value=float(current_count),
                expected_value=baseline,
                deviation_percentage=deviation_percentage,
                severity=severity,
                description=(
                    f"Total cookie count changed significantly: "
                    f"{current_count} cookies (expected ~{baseline:.0f}, "
                    f"{deviation_percentage:+.1f}% deviation)"
                )
            )
            
            logger.warning(
                f"Cookie count anomaly detected: {current_count} vs {baseline:.0f} "
                f"({deviation_percentage:.1f}% deviation, severity: {severity})"
            )
            
            return anomaly
        
        return None
    
    def _detect_compliance_score_anomaly(
        self,
        current_scan: ScanResult,
        historical_scans: List[ScanResult]
    ) -> Optional[Anomaly]:
        """Detect anomalies in compliance score."""
        current_score = self.metrics_calculator.calculate_compliance_score(current_scan)
        historical_scores = [
            self.metrics_calculator.calculate_compliance_score(scan)
            for scan in historical_scans
        ]
        
        baseline = statistics.mean(historical_scores)
        
        if baseline == 0:
            return None
        
        # Calculate deviation
        deviation_percentage = abs((current_score - baseline) / baseline * 100)
        
        # For compliance scores, we're especially concerned about drops
        score_drop = baseline - current_score
        
        if deviation_percentage >= self.threshold or score_drop > 10:
            severity = self._calculate_severity(deviation_percentage)
            
            # Increase severity if score dropped significantly
            if score_drop > 20:
                severity = 'high'
            elif score_drop > 10:
                severity = 'medium' if severity == 'low' else severity
            
            anomaly = Anomaly(
                anomaly_id=uuid4(),
                scan_id=current_scan.scan_id,
                domain=current_scan.domain,
                detected_at=datetime.utcnow(),
                anomaly_type='compliance_score_change',
                metric='compliance_score',
                current_value=current_score,
                expected_value=baseline,
                deviation_percentage=deviation_percentage,
                severity=severity,
                description=(
                    f"Compliance score changed: {current_score:.1f} "
                    f"(expected ~{baseline:.1f}, {score_drop:+.1f} point change)"
                )
            )
            
            logger.warning(
                f"Compliance score anomaly detected: {current_score:.1f} vs {baseline:.1f} "
                f"(severity: {severity})"
            )
            
            return anomaly
        
        return None
    
    def _detect_third_party_ratio_anomaly(
        self,
        current_scan: ScanResult,
        historical_scans: List[ScanResult]
    ) -> Optional[Anomaly]:
        """Detect anomalies in third-party cookie ratio."""
        # Calculate current ratio
        current_dist = self.metrics_calculator.calculate_party_distribution(current_scan)
        total_current = sum(current_dist.values())
        current_ratio = (
            current_dist.get('Third Party', 0) / total_current
            if total_current > 0 else 0.0
        )
        
        # Calculate historical baseline
        historical_ratios = []
        for scan in historical_scans:
            dist = self.metrics_calculator.calculate_party_distribution(scan)
            total = sum(dist.values())
            ratio = dist.get('Third Party', 0) / total if total > 0 else 0.0
            historical_ratios.append(ratio)
        
        baseline = statistics.mean(historical_ratios)
        
        if baseline == 0:
            return None
        
        # Calculate deviation
        deviation_percentage = abs((current_ratio - baseline) / baseline * 100)
        
        if deviation_percentage >= self.threshold:
            severity = self._calculate_severity(deviation_percentage)
            
            anomaly = Anomaly(
                anomaly_id=uuid4(),
                scan_id=current_scan.scan_id,
                domain=current_scan.domain,
                detected_at=datetime.utcnow(),
                anomaly_type='third_party_ratio_change',
                metric='third_party_ratio',
                current_value=current_ratio,
                expected_value=baseline,
                deviation_percentage=deviation_percentage,
                severity=severity,
                description=(
                    f"Third-party cookie ratio changed: {current_ratio:.1%} "
                    f"(expected ~{baseline:.1%}, {deviation_percentage:+.1f}% deviation)"
                )
            )
            
            logger.warning(
                f"Third-party ratio anomaly detected: {current_ratio:.1%} vs {baseline:.1%} "
                f"(severity: {severity})"
            )
            
            return anomaly
        
        return None
    
    def _detect_category_anomalies(
        self,
        current_scan: ScanResult,
        historical_scans: List[ScanResult]
    ) -> List[Anomaly]:
        """Detect anomalies in cookie category distributions."""
        anomalies = []
        
        # Get current distribution
        current_dist = self.metrics_calculator.calculate_cookie_distribution(current_scan)
        
        # Calculate baseline for each category
        category_baselines: Dict[str, List[int]] = {}
        for scan in historical_scans:
            dist = self.metrics_calculator.calculate_cookie_distribution(scan)
            for category, count in dist.items():
                if category not in category_baselines:
                    category_baselines[category] = []
                category_baselines[category].append(count)
        
        # Check each category in current scan
        for category, current_count in current_dist.items():
            if category not in category_baselines:
                continue  # New category, handled separately
            
            baseline = statistics.mean(category_baselines[category])
            
            if baseline == 0:
                continue
            
            deviation_percentage = abs((current_count - baseline) / baseline * 100)
            
            if deviation_percentage >= self.threshold:
                severity = self._calculate_severity(deviation_percentage)
                
                anomaly = Anomaly(
                    anomaly_id=uuid4(),
                    scan_id=current_scan.scan_id,
                    domain=current_scan.domain,
                    detected_at=datetime.utcnow(),
                    anomaly_type='category_distribution_change',
                    metric=f'category_{category}',
                    current_value=float(current_count),
                    expected_value=baseline,
                    deviation_percentage=deviation_percentage,
                    severity=severity,
                    description=(
                        f"{category} cookie count changed: {current_count} "
                        f"(expected ~{baseline:.0f}, {deviation_percentage:+.1f}% deviation)"
                    )
                )
                
                anomalies.append(anomaly)
                
                logger.warning(
                    f"Category anomaly detected for {category}: "
                    f"{current_count} vs {baseline:.0f} (severity: {severity})"
                )
        
        return anomalies
    
    def _detect_new_categories(
        self,
        current_scan: ScanResult,
        historical_scans: List[ScanResult]
    ) -> List[Anomaly]:
        """Detect new cookie categories that weren't in historical data."""
        anomalies = []
        
        # Get all historical categories
        historical_categories = set()
        for scan in historical_scans:
            dist = self.metrics_calculator.calculate_cookie_distribution(scan)
            historical_categories.update(dist.keys())
        
        # Get current categories
        current_dist = self.metrics_calculator.calculate_cookie_distribution(current_scan)
        current_categories = set(current_dist.keys())
        
        # Find new categories
        new_categories = current_categories - historical_categories
        
        for category in new_categories:
            count = current_dist[category]
            
            anomaly = Anomaly(
                anomaly_id=uuid4(),
                scan_id=current_scan.scan_id,
                domain=current_scan.domain,
                detected_at=datetime.utcnow(),
                anomaly_type='new_category_detected',
                metric=f'category_{category}',
                current_value=float(count),
                expected_value=0.0,
                deviation_percentage=100.0,
                severity='medium',
                description=(
                    f"New cookie category detected: {category} ({count} cookies)"
                )
            )
            
            anomalies.append(anomaly)
            
            logger.warning(
                f"New category detected: {category} with {count} cookies"
            )
        
        return anomalies
    
    def _calculate_severity(self, deviation_percentage: float) -> str:
        """
        Calculate severity level based on deviation percentage.
        
        Args:
            deviation_percentage: Percentage deviation from baseline
            
        Returns:
            Severity level: 'low', 'medium', or 'high'
        """
        if deviation_percentage >= self.SEVERITY_THRESHOLDS['high']:
            return 'high'
        elif deviation_percentage >= self.SEVERITY_THRESHOLDS['medium']:
            return 'medium'
        else:
            return 'low'
    
    def get_anomaly_summary(self, anomalies: List[Anomaly]) -> Dict[str, Any]:
        """
        Generate summary statistics for detected anomalies.
        
        Args:
            anomalies: List of detected anomalies
            
        Returns:
            Dictionary with anomaly summary
        """
        if not anomalies:
            return {
                'total_anomalies': 0,
                'by_severity': {'low': 0, 'medium': 0, 'high': 0},
                'by_type': {}
            }
        
        # Count by severity
        by_severity = {'low': 0, 'medium': 0, 'high': 0}
        for anomaly in anomalies:
            by_severity[anomaly.severity] += 1
        
        # Count by type
        by_type: Dict[str, int] = {}
        for anomaly in anomalies:
            by_type[anomaly.anomaly_type] = by_type.get(anomaly.anomaly_type, 0) + 1
        
        summary = {
            'total_anomalies': len(anomalies),
            'by_severity': by_severity,
            'by_type': by_type,
            'highest_severity': max(
                anomalies,
                key=lambda a: ['low', 'medium', 'high'].index(a.severity)
            ).severity if anomalies else None
        }
        
        logger.info(f"Anomaly summary: {summary}")
        return summary
