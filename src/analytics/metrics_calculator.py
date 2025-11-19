"""
Metrics calculator for cookie compliance and analytics.

Implements:
- Compliance score calculation
- Cookie distribution analysis
- Category aggregation
"""

import logging
from typing import Dict, List, Optional
from collections import Counter
from src.models.scan import ScanResult, Cookie, CookieType
from src.models.report import ComplianceMetrics

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculate metrics and KPIs from scan results."""
    
    # Category weights for compliance scoring
    CATEGORY_WEIGHTS = {
        'Necessary': 1.0,      # Fully compliant
        'Functional': 0.9,     # Generally acceptable
        'Analytics': 0.7,      # Requires consent
        'Advertising': 0.5,    # Requires explicit consent
        'Marketing': 0.5,      # Requires explicit consent
        'Targeting': 0.4,      # High privacy concern
        'Unknown': 0.3,        # Uncategorized is concerning
        'Uncategorized': 0.3   # Uncategorized is concerning
    }
    
    def __init__(self):
        """Initialize metrics calculator."""
        logger.info("MetricsCalculator initialized")
    
    def calculate_compliance_score(self, scan_result: ScanResult) -> float:
        """
        Calculate compliance score (0-100) based on cookie categories and types.
        
        The score considers:
        - Cookie categories (Necessary cookies score higher)
        - First-party vs third-party ratio
        - Cookies set before vs after consent
        
        Args:
            scan_result: Scan result to analyze
            
        Returns:
            Compliance score between 0 and 100
        """
        if not scan_result.cookies:
            logger.warning(f"No cookies found in scan {scan_result.scan_id}, returning score 100")
            return 100.0
        
        total_cookies = len(scan_result.cookies)
        
        # Calculate category-based score (60% weight)
        category_score = self._calculate_category_score(scan_result.cookies)
        
        # Calculate party type score (20% weight)
        party_score = self._calculate_party_score(scan_result.cookies)
        
        # Calculate consent score (20% weight)
        consent_score = self._calculate_consent_score(scan_result.cookies)
        
        # Weighted average
        compliance_score = (
            category_score * 0.6 +
            party_score * 0.2 +
            consent_score * 0.2
        )
        
        logger.info(
            f"Compliance score for scan {scan_result.scan_id}: {compliance_score:.2f} "
            f"(category: {category_score:.2f}, party: {party_score:.2f}, consent: {consent_score:.2f})"
        )
        
        return round(compliance_score, 2)
    
    def _calculate_category_score(self, cookies: List[Cookie]) -> float:
        """Calculate score based on cookie categories."""
        if not cookies:
            return 100.0
        
        total_weight = 0.0
        for cookie in cookies:
            category = cookie.category or 'Unknown'
            weight = self.CATEGORY_WEIGHTS.get(category, 0.3)
            total_weight += weight
        
        # Normalize to 0-100 scale
        avg_weight = total_weight / len(cookies)
        return avg_weight * 100
    
    def _calculate_party_score(self, cookies: List[Cookie]) -> float:
        """Calculate score based on first-party vs third-party ratio."""
        if not cookies:
            return 100.0
        
        first_party_count = sum(
            1 for c in cookies 
            if c.cookie_type == CookieType.FIRST_PARTY
        )
        
        # Higher ratio of first-party cookies = better score
        first_party_ratio = first_party_count / len(cookies)
        return first_party_ratio * 100
    
    def _calculate_consent_score(self, cookies: List[Cookie]) -> float:
        """Calculate score based on cookies set before/after consent."""
        if not cookies:
            return 100.0
        
        # Cookies set after consent are better for compliance
        after_consent_count = sum(1 for c in cookies if c.set_after_accept)
        
        # If all cookies are set after consent, perfect score
        if after_consent_count == len(cookies):
            return 100.0
        
        # Otherwise, score based on ratio
        after_consent_ratio = after_consent_count / len(cookies)
        return after_consent_ratio * 100
    
    def calculate_cookie_distribution(self, scan_result: ScanResult) -> Dict[str, int]:
        """
        Calculate cookie distribution by category.
        
        Args:
            scan_result: Scan result to analyze
            
        Returns:
            Dictionary mapping category names to cookie counts
        """
        if not scan_result.cookies:
            logger.info(f"No cookies in scan {scan_result.scan_id}")
            return {}
        
        categories = [cookie.category or 'Unknown' for cookie in scan_result.cookies]
        distribution = dict(Counter(categories))
        
        logger.info(
            f"Cookie distribution for scan {scan_result.scan_id}: {distribution}"
        )
        
        return distribution
    
    def aggregate_by_category(self, scan_result: ScanResult) -> Dict[str, List[Cookie]]:
        """
        Aggregate cookies by category.
        
        Args:
            scan_result: Scan result to analyze
            
        Returns:
            Dictionary mapping category names to lists of cookies
        """
        aggregated: Dict[str, List[Cookie]] = {}
        
        for cookie in scan_result.cookies:
            category = cookie.category or 'Unknown'
            if category not in aggregated:
                aggregated[category] = []
            aggregated[category].append(cookie)
        
        logger.info(
            f"Aggregated {len(scan_result.cookies)} cookies into "
            f"{len(aggregated)} categories for scan {scan_result.scan_id}"
        )
        
        return aggregated
    
    def calculate_party_distribution(self, scan_result: ScanResult) -> Dict[str, int]:
        """
        Calculate distribution of first-party vs third-party cookies.
        
        Args:
            scan_result: Scan result to analyze
            
        Returns:
            Dictionary with 'First Party' and 'Third Party' counts
        """
        if not scan_result.cookies:
            return {'First Party': 0, 'Third Party': 0}
        
        party_types = []
        for cookie in scan_result.cookies:
            if cookie.cookie_type:
                # Handle both enum and string values
                if hasattr(cookie.cookie_type, 'value'):
                    party_types.append(cookie.cookie_type.value)
                else:
                    party_types.append(str(cookie.cookie_type))
            else:
                party_types.append('Unknown')
        
        distribution = dict(Counter(party_types))
        
        # Ensure both keys exist
        result = {
            'First Party': distribution.get('First Party', 0),
            'Third Party': distribution.get('Third Party', 0),
            'Unknown': distribution.get('Unknown', 0)
        }
        
        logger.info(
            f"Party distribution for scan {scan_result.scan_id}: {result}"
        )
        
        return result
    
    def calculate_consent_metrics(self, scan_result: ScanResult) -> Dict[str, int]:
        """
        Calculate metrics related to cookie consent.
        
        Args:
            scan_result: Scan result to analyze
            
        Returns:
            Dictionary with before/after consent counts
        """
        if not scan_result.cookies:
            return {
                'set_before_accept': 0,
                'set_after_accept': 0,
                'total': 0
            }
        
        after_accept = sum(1 for c in scan_result.cookies if c.set_after_accept)
        before_accept = len(scan_result.cookies) - after_accept
        
        result = {
            'set_before_accept': before_accept,
            'set_after_accept': after_accept,
            'total': len(scan_result.cookies)
        }
        
        logger.info(
            f"Consent metrics for scan {scan_result.scan_id}: {result}"
        )
        
        return result
    
    def calculate_comprehensive_metrics(
        self,
        scan_result: ScanResult
    ) -> ComplianceMetrics:
        """
        Calculate comprehensive compliance metrics.
        
        Args:
            scan_result: Scan result to analyze
            
        Returns:
            ComplianceMetrics object with all calculated metrics
        """
        logger.info(f"Calculating comprehensive metrics for scan {scan_result.scan_id}")
        
        # Calculate all metrics
        compliance_score = self.calculate_compliance_score(scan_result)
        cookies_by_category = self.calculate_cookie_distribution(scan_result)
        cookies_by_type = self.calculate_party_distribution(scan_result)
        consent_metrics = self.calculate_consent_metrics(scan_result)
        
        # Calculate third-party ratio
        total_cookies = len(scan_result.cookies)
        third_party_count = cookies_by_type.get('Third Party', 0)
        third_party_ratio = (
            third_party_count / total_cookies if total_cookies > 0 else 0.0
        )
        
        metrics = ComplianceMetrics(
            total_cookies=total_cookies,
            cookies_by_category=cookies_by_category,
            cookies_by_type=cookies_by_type,
            compliance_score=compliance_score,
            third_party_ratio=round(third_party_ratio, 3),
            cookies_set_after_accept=consent_metrics['set_after_accept'],
            cookies_set_before_accept=consent_metrics['set_before_accept']
        )
        
        logger.info(
            f"Comprehensive metrics calculated for scan {scan_result.scan_id}: "
            f"score={compliance_score}, total={total_cookies}"
        )
        
        return metrics
    
    def calculate_vendor_distribution(self, scan_result: ScanResult) -> Dict[str, int]:
        """
        Calculate distribution of cookies by vendor.
        
        Args:
            scan_result: Scan result to analyze
            
        Returns:
            Dictionary mapping vendor names to cookie counts
        """
        if not scan_result.cookies:
            return {}
        
        vendors = [cookie.vendor or 'Unknown' for cookie in scan_result.cookies]
        distribution = dict(Counter(vendors))
        
        # Sort by count descending
        sorted_distribution = dict(
            sorted(distribution.items(), key=lambda x: x[1], reverse=True)
        )
        
        logger.info(
            f"Vendor distribution for scan {scan_result.scan_id}: "
            f"{len(sorted_distribution)} unique vendors"
        )
        
        return sorted_distribution
    
    def calculate_duration_distribution(self, scan_result: ScanResult) -> Dict[str, int]:
        """
        Calculate distribution of cookies by duration type.
        
        Args:
            scan_result: Scan result to analyze
            
        Returns:
            Dictionary mapping duration types to counts
        """
        if not scan_result.cookies:
            return {}
        
        # Categorize durations
        duration_categories = {
            'Session': 0,
            'Short-term (< 1 day)': 0,
            'Medium-term (1-30 days)': 0,
            'Long-term (> 30 days)': 0,
            'Unknown': 0
        }
        
        for cookie in scan_result.cookies:
            duration = cookie.cookie_duration or 'Unknown'
            
            if 'Session' in duration or 'session' in duration.lower():
                duration_categories['Session'] += 1
            elif 'Unknown' in duration or not duration:
                duration_categories['Unknown'] += 1
            else:
                # Try to parse duration (simplified)
                duration_lower = duration.lower()
                if 'hour' in duration_lower or ('day' in duration_lower and '1 day' in duration_lower):
                    duration_categories['Short-term (< 1 day)'] += 1
                elif 'day' in duration_lower:
                    # Extract number of days if possible
                    try:
                        days = int(''.join(filter(str.isdigit, duration)))
                        if days <= 30:
                            duration_categories['Medium-term (1-30 days)'] += 1
                        else:
                            duration_categories['Long-term (> 30 days)'] += 1
                    except:
                        duration_categories['Unknown'] += 1
                elif 'year' in duration_lower or 'month' in duration_lower:
                    duration_categories['Long-term (> 30 days)'] += 1
                else:
                    duration_categories['Unknown'] += 1
        
        logger.info(
            f"Duration distribution for scan {scan_result.scan_id}: {duration_categories}"
        )
        
        return duration_categories
