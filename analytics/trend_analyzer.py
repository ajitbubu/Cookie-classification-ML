"""
Trend analyzer for historical cookie data analysis.

Analyzes trends over time including:
- Cookie count trends
- Category distribution changes
- Compliance score trends
- Growth rates and averages
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import statistics

from models.scan import ScanResult
from models.report import TrendData
from analytics.metrics_calculator import MetricsCalculator

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Analyze historical trends in cookie data."""
    
    def __init__(
        self,
        metrics_calculator: Optional[MetricsCalculator] = None
    ):
        """
        Initialize trend analyzer.
        
        Args:
            metrics_calculator: Metrics calculator instance (creates new if None)
        """
        self.metrics_calculator = metrics_calculator or MetricsCalculator()
        logger.info("TrendAnalyzer initialized")
    
    def analyze_trends(
        self,
        domain: str,
        scan_results: List[ScanResult],
        metric: str = 'total_cookies'
    ) -> TrendData:
        """
        Analyze trends for a specific metric over time.
        
        Args:
            domain: Domain to analyze
            scan_results: List of historical scan results (sorted by timestamp)
            metric: Metric to analyze (total_cookies, compliance_score, third_party_ratio, etc.)
            
        Returns:
            TrendData object with analysis results
        """
        if not scan_results:
            logger.warning(f"No scan results provided for domain {domain}")
            raise ValueError("At least one scan result is required for trend analysis")
        
        # Sort by timestamp
        sorted_results = sorted(scan_results, key=lambda x: x.timestamp_utc)
        
        logger.info(
            f"Analyzing {metric} trend for {domain} with {len(sorted_results)} data points"
        )
        
        # Extract data points
        data_points = []
        for result in sorted_results:
            value = self._extract_metric_value(result, metric)
            data_points.append({
                'timestamp': result.timestamp_utc.isoformat(),
                'value': value,
                'scan_id': str(result.scan_id)
            })
        
        # Calculate trend direction and change
        trend_direction, change_percentage = self._calculate_trend_direction(
            [dp['value'] for dp in data_points]
        )
        
        # Create trend data
        trend_data = TrendData(
            domain=domain,
            metric=metric,
            time_range={
                'start': sorted_results[0].timestamp_utc,
                'end': sorted_results[-1].timestamp_utc
            },
            data_points=data_points,
            trend_direction=trend_direction,
            change_percentage=change_percentage
        )
        
        logger.info(
            f"Trend analysis complete for {domain}: {trend_direction} "
            f"({change_percentage:+.1f}% change)"
        )
        
        return trend_data
    
    def _extract_metric_value(self, scan_result: ScanResult, metric: str) -> float:
        """Extract metric value from scan result."""
        if metric == 'total_cookies':
            return float(len(scan_result.cookies))
        
        elif metric == 'compliance_score':
            return self.metrics_calculator.calculate_compliance_score(scan_result)
        
        elif metric == 'third_party_ratio':
            party_dist = self.metrics_calculator.calculate_party_distribution(scan_result)
            total = sum(party_dist.values())
            if total == 0:
                return 0.0
            return party_dist.get('Third Party', 0) / total
        
        elif metric == 'first_party_ratio':
            party_dist = self.metrics_calculator.calculate_party_distribution(scan_result)
            total = sum(party_dist.values())
            if total == 0:
                return 0.0
            return party_dist.get('First Party', 0) / total
        
        elif metric == 'cookies_after_consent':
            consent_metrics = self.metrics_calculator.calculate_consent_metrics(scan_result)
            return float(consent_metrics['set_after_accept'])
        
        elif metric == 'cookies_before_consent':
            consent_metrics = self.metrics_calculator.calculate_consent_metrics(scan_result)
            return float(consent_metrics['set_before_accept'])
        
        else:
            logger.warning(f"Unknown metric: {metric}, defaulting to total_cookies")
            return float(len(scan_result.cookies))
    
    def _calculate_trend_direction(
        self,
        values: List[float]
    ) -> Tuple[str, float]:
        """
        Calculate trend direction and percentage change.
        
        Args:
            values: List of metric values over time
            
        Returns:
            Tuple of (direction, change_percentage)
        """
        if len(values) < 2:
            return ('stable', 0.0)
        
        first_value = values[0]
        last_value = values[-1]
        
        # Calculate percentage change
        if first_value == 0:
            if last_value == 0:
                change_percentage = 0.0
            else:
                change_percentage = 100.0  # Infinite increase
        else:
            change_percentage = ((last_value - first_value) / first_value) * 100
        
        # Determine direction (threshold: 5% change)
        if abs(change_percentage) < 5:
            direction = 'stable'
        elif change_percentage > 0:
            direction = 'increasing'
        else:
            direction = 'decreasing'
        
        return (direction, change_percentage)
    
    def calculate_trend_metrics(
        self,
        scan_results: List[ScanResult],
        metric: str = 'total_cookies'
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive trend metrics.
        
        Args:
            scan_results: List of historical scan results
            metric: Metric to analyze
            
        Returns:
            Dictionary with trend metrics (average, min, max, growth_rate, etc.)
        """
        if not scan_results:
            return {}
        
        # Extract values
        values = [self._extract_metric_value(result, metric) for result in scan_results]
        
        # Calculate statistics
        metrics = {
            'count': len(values),
            'average': statistics.mean(values),
            'median': statistics.median(values),
            'min': min(values),
            'max': max(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0,
        }
        
        # Calculate growth rate (if applicable)
        if len(values) >= 2:
            sorted_results = sorted(scan_results, key=lambda x: x.timestamp_utc)
            time_span = (
                sorted_results[-1].timestamp_utc - sorted_results[0].timestamp_utc
            ).total_seconds() / 86400  # Convert to days
            
            if time_span > 0:
                first_value = values[0]
                last_value = values[-1]
                
                if first_value != 0:
                    total_change = ((last_value - first_value) / first_value) * 100
                    daily_growth_rate = total_change / time_span
                    metrics['growth_rate_per_day'] = daily_growth_rate
                    metrics['total_change_percentage'] = total_change
        
        logger.info(f"Trend metrics calculated: {metrics}")
        return metrics
    
    def analyze_category_trends(
        self,
        domain: str,
        scan_results: List[ScanResult]
    ) -> Dict[str, TrendData]:
        """
        Analyze trends for each cookie category.
        
        Args:
            domain: Domain to analyze
            scan_results: List of historical scan results
            
        Returns:
            Dictionary mapping category names to TrendData objects
        """
        if not scan_results:
            return {}
        
        logger.info(f"Analyzing category trends for {domain}")
        
        # Collect all categories
        all_categories = set()
        for result in scan_results:
            distribution = self.metrics_calculator.calculate_cookie_distribution(result)
            all_categories.update(distribution.keys())
        
        # Analyze trend for each category
        category_trends = {}
        for category in all_categories:
            data_points = []
            sorted_results = sorted(scan_results, key=lambda x: x.timestamp_utc)
            
            for result in sorted_results:
                distribution = self.metrics_calculator.calculate_cookie_distribution(result)
                count = distribution.get(category, 0)
                data_points.append({
                    'timestamp': result.timestamp_utc.isoformat(),
                    'value': count,
                    'scan_id': str(result.scan_id)
                })
            
            # Calculate trend
            values = [dp['value'] for dp in data_points]
            trend_direction, change_percentage = self._calculate_trend_direction(values)
            
            category_trends[category] = TrendData(
                domain=domain,
                metric=f'category_{category}',
                time_range={
                    'start': sorted_results[0].timestamp_utc,
                    'end': sorted_results[-1].timestamp_utc
                },
                data_points=data_points,
                trend_direction=trend_direction,
                change_percentage=change_percentage
            )
        
        logger.info(f"Category trends analyzed for {len(category_trends)} categories")
        return category_trends
    
    def get_moving_average(
        self,
        scan_results: List[ScanResult],
        metric: str = 'total_cookies',
        window_size: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Calculate moving average for a metric.
        
        Args:
            scan_results: List of historical scan results
            metric: Metric to analyze
            window_size: Size of moving average window
            
        Returns:
            List of data points with moving averages
        """
        if len(scan_results) < window_size:
            logger.warning(
                f"Not enough data points for moving average "
                f"(need {window_size}, have {len(scan_results)})"
            )
            return []
        
        sorted_results = sorted(scan_results, key=lambda x: x.timestamp_utc)
        values = [self._extract_metric_value(result, metric) for result in sorted_results]
        
        moving_averages = []
        for i in range(len(values) - window_size + 1):
            window = values[i:i + window_size]
            avg = statistics.mean(window)
            moving_averages.append({
                'timestamp': sorted_results[i + window_size - 1].timestamp_utc.isoformat(),
                'value': values[i + window_size - 1],
                'moving_average': avg,
                'scan_id': str(sorted_results[i + window_size - 1].scan_id)
            })
        
        logger.info(
            f"Moving average calculated with window size {window_size}: "
            f"{len(moving_averages)} data points"
        )
        
        return moving_averages
    
    def identify_trend_changes(
        self,
        scan_results: List[ScanResult],
        metric: str = 'total_cookies',
        threshold: float = 20.0
    ) -> List[Dict[str, Any]]:
        """
        Identify significant trend changes (inflection points).
        
        Args:
            scan_results: List of historical scan results
            metric: Metric to analyze
            threshold: Percentage change threshold to flag as significant
            
        Returns:
            List of trend change events
        """
        if len(scan_results) < 3:
            return []
        
        sorted_results = sorted(scan_results, key=lambda x: x.timestamp_utc)
        values = [self._extract_metric_value(result, metric) for result in sorted_results]
        
        trend_changes = []
        
        # Compare consecutive values
        for i in range(1, len(values)):
            prev_value = values[i - 1]
            curr_value = values[i]
            
            if prev_value == 0:
                continue
            
            change_percentage = ((curr_value - prev_value) / prev_value) * 100
            
            if abs(change_percentage) >= threshold:
                trend_changes.append({
                    'timestamp': sorted_results[i].timestamp_utc.isoformat(),
                    'scan_id': str(sorted_results[i].scan_id),
                    'previous_value': prev_value,
                    'current_value': curr_value,
                    'change_percentage': change_percentage,
                    'change_type': 'increase' if change_percentage > 0 else 'decrease'
                })
        
        logger.info(
            f"Identified {len(trend_changes)} significant trend changes "
            f"(threshold: {threshold}%)"
        )
        
        return trend_changes
    
    def compare_time_periods(
        self,
        domain: str,
        period1_results: List[ScanResult],
        period2_results: List[ScanResult],
        metric: str = 'total_cookies'
    ) -> Dict[str, Any]:
        """
        Compare metrics between two time periods.
        
        Args:
            domain: Domain being analyzed
            period1_results: Scan results from first period
            period2_results: Scan results from second period
            metric: Metric to compare
            
        Returns:
            Dictionary with comparison results
        """
        if not period1_results or not period2_results:
            logger.warning("Both periods must have scan results for comparison")
            return {}
        
        # Calculate metrics for each period
        period1_metrics = self.calculate_trend_metrics(period1_results, metric)
        period2_metrics = self.calculate_trend_metrics(period2_results, metric)
        
        # Calculate change
        avg_change = 0.0
        if period1_metrics.get('average', 0) != 0:
            avg_change = (
                (period2_metrics['average'] - period1_metrics['average']) /
                period1_metrics['average'] * 100
            )
        
        comparison = {
            'domain': domain,
            'metric': metric,
            'period1': {
                'count': period1_metrics['count'],
                'average': period1_metrics['average'],
                'min': period1_metrics['min'],
                'max': period1_metrics['max'],
                'time_range': {
                    'start': min(r.timestamp_utc for r in period1_results).isoformat(),
                    'end': max(r.timestamp_utc for r in period1_results).isoformat()
                }
            },
            'period2': {
                'count': period2_metrics['count'],
                'average': period2_metrics['average'],
                'min': period2_metrics['min'],
                'max': period2_metrics['max'],
                'time_range': {
                    'start': min(r.timestamp_utc for r in period2_results).isoformat(),
                    'end': max(r.timestamp_utc for r in period2_results).isoformat()
                }
            },
            'change': {
                'average_change_percentage': avg_change,
                'direction': 'increase' if avg_change > 0 else 'decrease' if avg_change < 0 else 'stable'
            }
        }
        
        logger.info(
            f"Period comparison complete: {avg_change:+.1f}% change in average {metric}"
        )
        
        return comparison
