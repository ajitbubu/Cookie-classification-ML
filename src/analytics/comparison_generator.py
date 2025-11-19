"""
Comparison report generator for cookie compliance analysis.

Supports:
- Temporal comparison (same domain over time)
- Cross-domain comparison
- Diff reports showing changes
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from pathlib import Path

from src.models.scan import ScanResult, Cookie
from src.models.report import Report, ReportType, ReportFormat
from src.analytics.metrics_calculator import MetricsCalculator

logger = logging.getLogger(__name__)


class ComparisonGenerator:
    """Generate comparison reports between scan results."""
    
    def __init__(
        self,
        output_dir: str = "results/reports",
        metrics_calculator: Optional[MetricsCalculator] = None
    ):
        """
        Initialize comparison generator.
        
        Args:
            output_dir: Directory to save generated reports
            metrics_calculator: Metrics calculator instance (creates new if None)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_calculator = metrics_calculator or MetricsCalculator()
        logger.info(f"ComparisonGenerator initialized with output_dir: {output_dir}")
    
    def generate_temporal_comparison(
        self,
        domain: str,
        scan_results: List[ScanResult],
        format: ReportFormat = ReportFormat.JSON
    ) -> Report:
        """
        Generate temporal comparison report (same domain over time).
        
        Args:
            domain: Domain being compared
            scan_results: List of scan results sorted by time
            format: Report format
            
        Returns:
            Report object with comparison data
        """
        if len(scan_results) < 2:
            raise ValueError("At least 2 scan results required for temporal comparison")
        
        logger.info(
            f"Generating temporal comparison for {domain} "
            f"with {len(scan_results)} scans"
        )
        
        # Sort by timestamp
        sorted_scans = sorted(scan_results, key=lambda x: x.timestamp_utc)
        
        # Calculate metrics for each scan
        metrics_timeline = []
        for scan in sorted_scans:
            metrics = self.metrics_calculator.calculate_comprehensive_metrics(scan)
            metrics_timeline.append({
                'scan_id': str(scan.scan_id),
                'timestamp': scan.timestamp_utc.isoformat(),
                'metrics': metrics.dict()
            })
        
        # Calculate changes between first and last scan
        first_scan = sorted_scans[0]
        last_scan = sorted_scans[-1]
        changes = self._calculate_changes(first_scan, last_scan)
        
        # Generate cookie diff
        cookie_diff = self._generate_cookie_diff(first_scan, last_scan)
        
        # Build comparison data
        comparison_data = {
            'comparison_type': 'temporal',
            'domain': domain,
            'time_range': {
                'start': first_scan.timestamp_utc.isoformat(),
                'end': last_scan.timestamp_utc.isoformat()
            },
            'scan_count': len(sorted_scans),
            'metrics_timeline': metrics_timeline,
            'changes': changes,
            'cookie_diff': cookie_diff
        }
        
        # Generate report file
        if format == ReportFormat.JSON:
            file_path = self._save_json_comparison(domain, comparison_data, 'temporal')
        elif format == ReportFormat.HTML:
            file_path = self._save_html_comparison(domain, comparison_data, 'temporal')
        else:
            raise ValueError(f"Unsupported format for comparison: {format}")
        
        # Get file size
        file_size = Path(file_path).stat().st_size if file_path else None
        
        # Create report object
        report = Report(
            report_type=ReportType.COMPARISON,
            format=format,
            generated_at=datetime.utcnow(),
            data=comparison_data,
            file_path=file_path,
            file_size=file_size
        )
        
        logger.info(f"Temporal comparison report generated: {file_path}")
        return report
    
    def generate_cross_domain_comparison(
        self,
        scan_results: List[ScanResult],
        format: ReportFormat = ReportFormat.JSON
    ) -> Report:
        """
        Generate cross-domain comparison report.
        
        Args:
            scan_results: List of scan results from different domains
            format: Report format
            
        Returns:
            Report object with comparison data
        """
        if len(scan_results) < 2:
            raise ValueError("At least 2 scan results required for cross-domain comparison")
        
        domains = [scan.domain for scan in scan_results]
        logger.info(f"Generating cross-domain comparison for {len(domains)} domains")
        
        # Calculate metrics for each domain
        domain_metrics = []
        for scan in scan_results:
            metrics = self.metrics_calculator.calculate_comprehensive_metrics(scan)
            domain_metrics.append({
                'domain': scan.domain,
                'scan_id': str(scan.scan_id),
                'timestamp': scan.timestamp_utc.isoformat(),
                'metrics': metrics.dict()
            })
        
        # Calculate comparative statistics
        comparative_stats = self._calculate_comparative_stats(scan_results)
        
        # Build comparison data
        comparison_data = {
            'comparison_type': 'cross_domain',
            'domains': domains,
            'scan_count': len(scan_results),
            'domain_metrics': domain_metrics,
            'comparative_stats': comparative_stats
        }
        
        # Generate report file
        if format == ReportFormat.JSON:
            file_path = self._save_json_comparison('cross_domain', comparison_data, 'cross_domain')
        elif format == ReportFormat.HTML:
            file_path = self._save_html_comparison('cross_domain', comparison_data, 'cross_domain')
        else:
            raise ValueError(f"Unsupported format for comparison: {format}")
        
        # Get file size
        file_size = Path(file_path).stat().st_size if file_path else None
        
        # Create report object
        report = Report(
            report_type=ReportType.COMPARISON,
            format=format,
            generated_at=datetime.utcnow(),
            data=comparison_data,
            file_path=file_path,
            file_size=file_size
        )
        
        logger.info(f"Cross-domain comparison report generated: {file_path}")
        return report
    
    def _calculate_changes(
        self,
        first_scan: ScanResult,
        last_scan: ScanResult
    ) -> Dict[str, Any]:
        """Calculate changes between two scans."""
        first_metrics = self.metrics_calculator.calculate_comprehensive_metrics(first_scan)
        last_metrics = self.metrics_calculator.calculate_comprehensive_metrics(last_scan)
        
        # Calculate absolute and percentage changes
        cookie_change = last_metrics.total_cookies - first_metrics.total_cookies
        cookie_change_pct = (
            (cookie_change / first_metrics.total_cookies * 100)
            if first_metrics.total_cookies > 0 else 0.0
        )
        
        score_change = last_metrics.compliance_score - first_metrics.compliance_score
        
        third_party_change = (
            last_metrics.third_party_ratio - first_metrics.third_party_ratio
        )
        
        changes = {
            'total_cookies': {
                'first': first_metrics.total_cookies,
                'last': last_metrics.total_cookies,
                'change': cookie_change,
                'change_percentage': cookie_change_pct
            },
            'compliance_score': {
                'first': first_metrics.compliance_score,
                'last': last_metrics.compliance_score,
                'change': score_change
            },
            'third_party_ratio': {
                'first': first_metrics.third_party_ratio,
                'last': last_metrics.third_party_ratio,
                'change': third_party_change
            },
            'category_changes': self._calculate_category_changes(
                first_metrics.cookies_by_category,
                last_metrics.cookies_by_category
            )
        }
        
        return changes
    
    def _calculate_category_changes(
        self,
        first_categories: Dict[str, int],
        last_categories: Dict[str, int]
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate changes in category distribution."""
        all_categories = set(first_categories.keys()) | set(last_categories.keys())
        
        category_changes = {}
        for category in all_categories:
            first_count = first_categories.get(category, 0)
            last_count = last_categories.get(category, 0)
            change = last_count - first_count
            
            change_pct = 0.0
            if first_count > 0:
                change_pct = (change / first_count) * 100
            elif last_count > 0:
                change_pct = 100.0  # New category
            
            category_changes[category] = {
                'first': first_count,
                'last': last_count,
                'change': change,
                'change_percentage': change_pct
            }
        
        return category_changes
    
    def _generate_cookie_diff(
        self,
        first_scan: ScanResult,
        last_scan: ScanResult
    ) -> Dict[str, Any]:
        """Generate diff of cookies between two scans."""
        # Create sets of cookie identifiers (name + domain)
        first_cookies = {
            (c.name, c.domain): c for c in first_scan.cookies
        }
        last_cookies = {
            (c.name, c.domain): c for c in last_scan.cookies
        }
        
        first_keys = set(first_cookies.keys())
        last_keys = set(last_cookies.keys())
        
        # Find added, removed, and common cookies
        added_keys = last_keys - first_keys
        removed_keys = first_keys - last_keys
        common_keys = first_keys & last_keys
        
        # Check for changes in common cookies
        modified = []
        for key in common_keys:
            first_cookie = first_cookies[key]
            last_cookie = last_cookies[key]
            
            # Check if category or other properties changed
            if (first_cookie.category != last_cookie.category or
                first_cookie.cookie_type != last_cookie.cookie_type):
                modified.append({
                    'name': key[0],
                    'domain': key[1],
                    'changes': {
                        'category': {
                            'from': first_cookie.category,
                            'to': last_cookie.category
                        },
                        'type': {
                            'from': first_cookie.cookie_type.value if first_cookie.cookie_type else None,
                            'to': last_cookie.cookie_type.value if last_cookie.cookie_type else None
                        }
                    }
                })
        
        diff = {
            'added': [
                {'name': key[0], 'domain': key[1], 'category': last_cookies[key].category}
                for key in added_keys
            ],
            'removed': [
                {'name': key[0], 'domain': key[1], 'category': first_cookies[key].category}
                for key in removed_keys
            ],
            'modified': modified,
            'summary': {
                'added_count': len(added_keys),
                'removed_count': len(removed_keys),
                'modified_count': len(modified),
                'unchanged_count': len(common_keys) - len(modified)
            }
        }
        
        return diff
    
    def _calculate_comparative_stats(
        self,
        scan_results: List[ScanResult]
    ) -> Dict[str, Any]:
        """Calculate comparative statistics across domains."""
        import statistics
        
        # Collect metrics for all domains
        all_metrics = [
            self.metrics_calculator.calculate_comprehensive_metrics(scan)
            for scan in scan_results
        ]
        
        # Calculate statistics
        cookie_counts = [m.total_cookies for m in all_metrics]
        compliance_scores = [m.compliance_score for m in all_metrics]
        third_party_ratios = [m.third_party_ratio for m in all_metrics]
        
        stats = {
            'total_cookies': {
                'min': min(cookie_counts),
                'max': max(cookie_counts),
                'average': statistics.mean(cookie_counts),
                'median': statistics.median(cookie_counts)
            },
            'compliance_score': {
                'min': min(compliance_scores),
                'max': max(compliance_scores),
                'average': statistics.mean(compliance_scores),
                'median': statistics.median(compliance_scores)
            },
            'third_party_ratio': {
                'min': min(third_party_ratios),
                'max': max(third_party_ratios),
                'average': statistics.mean(third_party_ratios),
                'median': statistics.median(third_party_ratios)
            }
        }
        
        return stats
    
    def _save_json_comparison(
        self,
        identifier: str,
        data: Dict[str, Any],
        comparison_type: str
    ) -> str:
        """Save comparison report as JSON."""
        import json
        
        filename = f"comparison_{comparison_type}_{identifier}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        file_path = self.output_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"JSON comparison saved: {file_path}")
        return str(file_path)
    
    def _save_html_comparison(
        self,
        identifier: str,
        data: Dict[str, Any],
        comparison_type: str
    ) -> str:
        """Save comparison report as HTML."""
        filename = f"comparison_{comparison_type}_{identifier}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.html"
        file_path = self.output_dir / filename
        
        if comparison_type == 'temporal':
            html_content = self._generate_temporal_html(data)
        else:
            html_content = self._generate_cross_domain_html(data)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML comparison saved: {file_path}")
        return str(file_path)
    
    def _generate_temporal_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML for temporal comparison."""
        changes = data['changes']
        cookie_diff = data['cookie_diff']
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Temporal Comparison - {data['domain']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1a1a1a; border-bottom: 3px solid #2e7d32; padding-bottom: 10px; }}
        h2 {{ color: #333; margin-top: 30px; }}
        .metric {{ background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .positive {{ color: #2e7d32; }}
        .negative {{ color: #c62828; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border: 1px solid #ddd; }}
        th {{ background-color: #666; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
    </style>
</head>
<body>
    <h1>Temporal Comparison Report</h1>
    <p><strong>Domain:</strong> {data['domain']}</p>
    <p><strong>Time Range:</strong> {data['time_range']['start']} to {data['time_range']['end']}</p>
    <p><strong>Scans Analyzed:</strong> {data['scan_count']}</p>
    
    <h2>Key Changes</h2>
    <div class="metric">
        <strong>Total Cookies:</strong> {changes['total_cookies']['first']} → {changes['total_cookies']['last']}
        <span class="{'positive' if changes['total_cookies']['change'] < 0 else 'negative'}">
            ({changes['total_cookies']['change']:+d}, {changes['total_cookies']['change_percentage']:+.1f}%)
        </span>
    </div>
    <div class="metric">
        <strong>Compliance Score:</strong> {changes['compliance_score']['first']:.1f} → {changes['compliance_score']['last']:.1f}
        <span class="{'positive' if changes['compliance_score']['change'] > 0 else 'negative'}">
            ({changes['compliance_score']['change']:+.1f} points)
        </span>
    </div>
    <div class="metric">
        <strong>Third-Party Ratio:</strong> {changes['third_party_ratio']['first']:.1%} → {changes['third_party_ratio']['last']:.1%}
        <span class="{'positive' if changes['third_party_ratio']['change'] < 0 else 'negative'}">
            ({changes['third_party_ratio']['change']:+.1%})
        </span>
    </div>
    
    <h2>Cookie Changes</h2>
    <p><strong>Added:</strong> {cookie_diff['summary']['added_count']} cookies</p>
    <p><strong>Removed:</strong> {cookie_diff['summary']['removed_count']} cookies</p>
    <p><strong>Modified:</strong> {cookie_diff['summary']['modified_count']} cookies</p>
    <p><strong>Unchanged:</strong> {cookie_diff['summary']['unchanged_count']} cookies</p>
    
    <div class="footer" style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666;">
        Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
    </div>
</body>
</html>
"""
        return html
    
    def _generate_cross_domain_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML for cross-domain comparison."""
        stats = data['comparative_stats']
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cross-Domain Comparison</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1a1a1a; border-bottom: 3px solid #2e7d32; padding-bottom: 10px; }}
        h2 {{ color: #333; margin-top: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border: 1px solid #ddd; }}
        th {{ background-color: #666; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
    </style>
</head>
<body>
    <h1>Cross-Domain Comparison Report</h1>
    <p><strong>Domains Compared:</strong> {len(data['domains'])}</p>
    
    <h2>Comparative Statistics</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Min</th>
            <th>Max</th>
            <th>Average</th>
            <th>Median</th>
        </tr>
        <tr>
            <td>Total Cookies</td>
            <td>{stats['total_cookies']['min']}</td>
            <td>{stats['total_cookies']['max']}</td>
            <td>{stats['total_cookies']['average']:.1f}</td>
            <td>{stats['total_cookies']['median']:.1f}</td>
        </tr>
        <tr>
            <td>Compliance Score</td>
            <td>{stats['compliance_score']['min']:.1f}</td>
            <td>{stats['compliance_score']['max']:.1f}</td>
            <td>{stats['compliance_score']['average']:.1f}</td>
            <td>{stats['compliance_score']['median']:.1f}</td>
        </tr>
        <tr>
            <td>Third-Party Ratio</td>
            <td>{stats['third_party_ratio']['min']:.1%}</td>
            <td>{stats['third_party_ratio']['max']:.1%}</td>
            <td>{stats['third_party_ratio']['average']:.1%}</td>
            <td>{stats['third_party_ratio']['median']:.1%}</td>
        </tr>
    </table>
    
    <h2>Domain Details</h2>
    <table>
        <tr>
            <th>Domain</th>
            <th>Total Cookies</th>
            <th>Compliance Score</th>
            <th>Third-Party Ratio</th>
        </tr>
"""
        
        for domain_data in data['domain_metrics']:
            metrics = domain_data['metrics']
            html += f"""
        <tr>
            <td>{domain_data['domain']}</td>
            <td>{metrics['total_cookies']}</td>
            <td>{metrics['compliance_score']:.1f}</td>
            <td>{metrics['third_party_ratio']:.1%}</td>
        </tr>
"""
        
        html += f"""
    </table>
    
    <div class="footer" style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666;">
        Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
    </div>
</body>
</html>
"""
        return html
