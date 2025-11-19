"""
Simple test to verify analytics module functionality.
"""

from datetime import datetime
from uuid import uuid4

from src.models.scan import ScanResult, Cookie, ScanParams, ScanMode, ScanStatus, CookieType
from analytics import (
    MetricsCalculator,
    ReportGenerator,
    TrendAnalyzer,
    AnomalyDetector,
    ComparisonGenerator
)
from src.models.report import ReportFormat


def create_test_scan(domain: str, cookie_count: int = 10) -> ScanResult:
    """Create a test scan result."""
    cookies = []
    for i in range(cookie_count):
        cookies.append(Cookie(
            name=f"cookie_{i}",
            domain=domain,
            path="/",
            category="Necessary" if i < 3 else "Analytics" if i < 7 else "Advertising",
            cookie_type=CookieType.FIRST_PARTY if i < 6 else CookieType.THIRD_PARTY,
            set_after_accept=i >= 5,
            vendor=f"Vendor_{i % 3}",
            cookie_duration="30 days" if i < 8 else "Session"
        ))
    
    return ScanResult(
        scan_id=uuid4(),
        domain_config_id=uuid4(),
        domain=domain,
        scan_mode=ScanMode.QUICK,
        timestamp_utc=datetime.utcnow(),
        status=ScanStatus.SUCCESS,
        duration_seconds=45.5,
        total_cookies=len(cookies),
        page_count=5,
        params=ScanParams(),
        cookies=cookies
    )


def test_metrics_calculator():
    """Test metrics calculator."""
    print("\n=== Testing MetricsCalculator ===")
    
    calculator = MetricsCalculator()
    scan = create_test_scan("example.com", cookie_count=10)
    
    # Test compliance score
    score = calculator.calculate_compliance_score(scan)
    print(f"✓ Compliance Score: {score:.2f}/100")
    assert 0 <= score <= 100, "Score should be between 0 and 100"
    
    # Test cookie distribution
    distribution = calculator.calculate_cookie_distribution(scan)
    print(f"✓ Cookie Distribution: {distribution}")
    assert sum(distribution.values()) == 10, "Total should be 10 cookies"
    
    # Test party distribution
    party_dist = calculator.calculate_party_distribution(scan)
    print(f"✓ Party Distribution: {party_dist}")
    
    # Test comprehensive metrics
    metrics = calculator.calculate_comprehensive_metrics(scan)
    print(f"✓ Comprehensive Metrics: total={metrics.total_cookies}, score={metrics.compliance_score:.1f}")
    assert metrics.total_cookies == 10
    
    print("✅ MetricsCalculator tests passed!")


def test_report_generator():
    """Test report generator."""
    print("\n=== Testing ReportGenerator ===")
    
    generator = ReportGenerator(output_dir="results/reports")
    scan = create_test_scan("example.com", cookie_count=10)
    
    # Test JSON report
    report = generator.generate_compliance_report(scan, format=ReportFormat.JSON)
    print(f"✓ JSON Report generated: {report.file_path}")
    assert report.file_path is not None
    assert report.file_size > 0
    
    # Test HTML report
    report = generator.generate_compliance_report(scan, format=ReportFormat.HTML)
    print(f"✓ HTML Report generated: {report.file_path}")
    assert report.file_path is not None
    
    # Test PDF report
    report = generator.generate_compliance_report(scan, format=ReportFormat.PDF)
    print(f"✓ PDF Report generated: {report.file_path}")
    assert report.file_path is not None
    
    # Test CSV export
    csv_path = generator.export_to_csv(scan)
    print(f"✓ CSV Export generated: {csv_path}")
    assert csv_path is not None
    
    print("✅ ReportGenerator tests passed!")


def test_trend_analyzer():
    """Test trend analyzer."""
    print("\n=== Testing TrendAnalyzer ===")
    
    analyzer = TrendAnalyzer()
    
    # Create historical scans with increasing cookie counts
    scans = [
        create_test_scan("example.com", cookie_count=10),
        create_test_scan("example.com", cookie_count=12),
        create_test_scan("example.com", cookie_count=15),
    ]
    
    # Adjust timestamps
    from datetime import timedelta
    for i, scan in enumerate(scans):
        scan.timestamp_utc = datetime.utcnow() - timedelta(days=len(scans) - i)
    
    # Test trend analysis
    trend_data = analyzer.analyze_trends(
        domain="example.com",
        scan_results=scans,
        metric='total_cookies'
    )
    print(f"✓ Trend Analysis: {trend_data.trend_direction} ({trend_data.change_percentage:+.1f}%)")
    assert trend_data.trend_direction == 'increasing'
    
    # Test trend metrics
    metrics = analyzer.calculate_trend_metrics(scans, metric='total_cookies')
    print(f"✓ Trend Metrics: avg={metrics['average']:.1f}, min={metrics['min']}, max={metrics['max']}")
    assert metrics['average'] > 0
    
    print("✅ TrendAnalyzer tests passed!")


def test_anomaly_detector():
    """Test anomaly detector."""
    print("\n=== Testing AnomalyDetector ===")
    
    detector = AnomalyDetector(threshold=20.0)
    
    # Create baseline scans
    baseline_scans = [
        create_test_scan("example.com", cookie_count=10),
        create_test_scan("example.com", cookie_count=11),
        create_test_scan("example.com", cookie_count=9),
    ]
    
    # Create anomalous scan (50% increase)
    anomalous_scan = create_test_scan("example.com", cookie_count=15)
    
    # Detect anomalies
    anomalies = detector.detect_anomalies(
        current_scan=anomalous_scan,
        historical_scans=baseline_scans
    )
    print(f"✓ Detected {len(anomalies)} anomalies")
    
    if anomalies:
        for anomaly in anomalies:
            print(f"  - [{anomaly.severity}] {anomaly.anomaly_type}: {anomaly.description}")
    
    # Test summary
    summary = detector.get_anomaly_summary(anomalies)
    print(f"✓ Anomaly Summary: {summary}")
    
    print("✅ AnomalyDetector tests passed!")


def test_comparison_generator():
    """Test comparison generator."""
    print("\n=== Testing ComparisonGenerator ===")
    
    generator = ComparisonGenerator(output_dir="results/reports")
    
    # Create scans for temporal comparison
    from datetime import timedelta
    scans = [
        create_test_scan("example.com", cookie_count=10),
        create_test_scan("example.com", cookie_count=12),
    ]
    scans[0].timestamp_utc = datetime.utcnow() - timedelta(days=7)
    scans[1].timestamp_utc = datetime.utcnow()
    
    # Test temporal comparison
    report = generator.generate_temporal_comparison(
        domain="example.com",
        scan_results=scans,
        format=ReportFormat.JSON
    )
    print(f"✓ Temporal Comparison generated: {report.file_path}")
    assert report.file_path is not None
    
    # Create scans for cross-domain comparison
    domain_scans = [
        create_test_scan("example.com", cookie_count=10),
        create_test_scan("test.com", cookie_count=15),
    ]
    
    # Test cross-domain comparison
    report = generator.generate_cross_domain_comparison(
        scan_results=domain_scans,
        format=ReportFormat.JSON
    )
    print(f"✓ Cross-Domain Comparison generated: {report.file_path}")
    assert report.file_path is not None
    
    print("✅ ComparisonGenerator tests passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("Analytics Module Test Suite")
    print("=" * 60)
    
    try:
        test_metrics_calculator()
        test_report_generator()
        test_trend_analyzer()
        test_anomaly_detector()
        test_comparison_generator()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
