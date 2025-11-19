# Analytics Module

The analytics module provides comprehensive cookie compliance analysis capabilities for the Cookie Scanner Platform.

## Components

### 1. MetricsCalculator (`metrics_calculator.py`)

Calculates compliance metrics and KPIs from scan results.

**Key Features:**
- Compliance score calculation (0-100 scale)
- Cookie distribution by category
- Party type distribution (first-party vs third-party)
- Consent metrics (before/after acceptance)
- Vendor and duration distribution

**Usage:**
```python
from analytics import MetricsCalculator
from models.scan import ScanResult

calculator = MetricsCalculator()

# Calculate comprehensive metrics
metrics = calculator.calculate_comprehensive_metrics(scan_result)
print(f"Compliance Score: {metrics.compliance_score}")
print(f"Total Cookies: {metrics.total_cookies}")
print(f"Third-Party Ratio: {metrics.third_party_ratio}")

# Calculate specific distributions
category_dist = calculator.calculate_cookie_distribution(scan_result)
party_dist = calculator.calculate_party_distribution(scan_result)
```

### 2. ReportGenerator (`report_generator.py`)

Generates compliance reports in multiple formats.

**Supported Formats:**
- PDF (using ReportLab)
- HTML (styled templates)
- JSON (API-friendly)
- CSV (cookie export)

**Usage:**
```python
from analytics import ReportGenerator
from models.report import ReportFormat

generator = ReportGenerator(output_dir="results/reports")

# Generate PDF report
report = generator.generate_compliance_report(
    scan_result,
    format=ReportFormat.PDF
)
print(f"Report saved to: {report.file_path}")

# Export cookies to CSV
csv_path = generator.export_to_csv(scan_result)
```

### 3. TrendAnalyzer (`trend_analyzer.py`)

Analyzes historical trends in cookie data.

**Key Features:**
- Trend analysis for any metric over time
- Moving averages
- Growth rate calculation
- Trend change detection
- Period comparison

**Usage:**
```python
from analytics import TrendAnalyzer

analyzer = TrendAnalyzer()

# Analyze trends
trend_data = analyzer.analyze_trends(
    domain="example.com",
    scan_results=historical_scans,
    metric='total_cookies'
)
print(f"Trend: {trend_data.trend_direction}")
print(f"Change: {trend_data.change_percentage:+.1f}%")

# Calculate trend metrics
metrics = analyzer.calculate_trend_metrics(
    scan_results=historical_scans,
    metric='compliance_score'
)
print(f"Average: {metrics['average']:.1f}")
print(f"Growth Rate: {metrics.get('growth_rate_per_day', 0):.2f}% per day")

# Identify significant changes
changes = analyzer.identify_trend_changes(
    scan_results=historical_scans,
    metric='total_cookies',
    threshold=20.0
)
```

### 4. AnomalyDetector (`anomaly_detector.py`)

Detects anomalies by comparing current scans with historical baselines.

**Detection Types:**
- Cookie count changes (>20% threshold)
- Compliance score drops
- Third-party ratio changes
- Category distribution anomalies
- New categories

**Usage:**
```python
from analytics import AnomalyDetector

detector = AnomalyDetector(threshold=20.0)

# Detect anomalies
anomalies = detector.detect_anomalies(
    current_scan=latest_scan,
    historical_scans=baseline_scans,
    min_history=3
)

for anomaly in anomalies:
    print(f"[{anomaly.severity.upper()}] {anomaly.description}")

# Get summary
summary = detector.get_anomaly_summary(anomalies)
print(f"Total anomalies: {summary['total_anomalies']}")
print(f"High severity: {summary['by_severity']['high']}")
```

### 5. ComparisonGenerator (`comparison_generator.py`)

Generates comparison reports between scan results.

**Comparison Types:**
- Temporal comparison (same domain over time)
- Cross-domain comparison
- Cookie diff reports

**Usage:**
```python
from analytics import ComparisonGenerator
from models.report import ReportFormat

generator = ComparisonGenerator(output_dir="results/reports")

# Temporal comparison
report = generator.generate_temporal_comparison(
    domain="example.com",
    scan_results=time_series_scans,
    format=ReportFormat.JSON
)

# Cross-domain comparison
report = generator.generate_cross_domain_comparison(
    scan_results=[scan1, scan2, scan3],
    format=ReportFormat.HTML
)
```

### 6. AnalyticsCacheManager (`cache_manager.py`)

Manages caching for analytics data using Redis.

**Key Features:**
- Cache computed metrics (1 hour TTL)
- Cache trend data (1 hour TTL)
- Cache reports (30 minutes TTL)
- Cache invalidation on new scans
- Cache warming for frequently accessed data

**Usage:**
```python
from analytics import AnalyticsCacheManager

cache_manager = AnalyticsCacheManager()

# Cache metrics
cache_manager.cache_metrics(scan_id, metrics)

# Get cached metrics
cached_metrics = cache_manager.get_cached_metrics(scan_id)

# Get or compute with caching
metrics = cache_manager.get_or_compute_metrics(
    scan_id,
    compute_fn=lambda: calculator.calculate_comprehensive_metrics(scan_result)
)

# Invalidate cache on new scan
cache_manager.invalidate_domain_cache(domain)

# Warm cache for multiple scans
cache_manager.warm_cache(
    scan_results=recent_scans,
    compute_metrics_fn=calculator.calculate_comprehensive_metrics
)
```

## Integration Example

Complete workflow using all components:

```python
from analytics import (
    MetricsCalculator,
    ReportGenerator,
    TrendAnalyzer,
    AnomalyDetector,
    ComparisonGenerator,
    AnalyticsCacheManager
)
from models.scan import ScanResult
from models.report import ReportFormat

# Initialize components
calculator = MetricsCalculator()
report_gen = ReportGenerator()
trend_analyzer = TrendAnalyzer(metrics_calculator=calculator)
anomaly_detector = AnomalyDetector(metrics_calculator=calculator)
comparison_gen = ComparisonGenerator(metrics_calculator=calculator)
cache_manager = AnalyticsCacheManager()

# Process new scan
def process_scan(scan_result: ScanResult, historical_scans: list):
    # Calculate metrics (with caching)
    metrics = cache_manager.get_or_compute_metrics(
        str(scan_result.scan_id),
        lambda: calculator.calculate_comprehensive_metrics(scan_result)
    )
    
    # Generate compliance report
    report = report_gen.generate_compliance_report(
        scan_result,
        format=ReportFormat.PDF
    )
    
    # Analyze trends
    if len(historical_scans) >= 2:
        trend_data = trend_analyzer.analyze_trends(
            domain=scan_result.domain,
            scan_results=historical_scans + [scan_result],
            metric='compliance_score'
        )
    
    # Detect anomalies
    if len(historical_scans) >= 3:
        anomalies = anomaly_detector.detect_anomalies(
            current_scan=scan_result,
            historical_scans=historical_scans
        )
        
        if anomalies:
            print(f"⚠️  {len(anomalies)} anomalies detected!")
    
    # Invalidate cache for domain (to refresh trends)
    cache_manager.invalidate_domain_cache(scan_result.domain)
    
    return {
        'metrics': metrics,
        'report': report,
        'trend_data': trend_data if len(historical_scans) >= 2 else None,
        'anomalies': anomalies if len(historical_scans) >= 3 else []
    }
```

## Configuration

### Cache TTLs

Default cache TTLs can be customized:

```python
from analytics import AnalyticsCacheManager

cache_manager = AnalyticsCacheManager()
cache_manager.CACHE_TTLS['metrics'] = 7200  # 2 hours
cache_manager.CACHE_TTLS['trends'] = 1800   # 30 minutes
```

### Compliance Score Weights

Category weights for compliance scoring can be adjusted:

```python
from analytics import MetricsCalculator

calculator = MetricsCalculator()
calculator.CATEGORY_WEIGHTS['Necessary'] = 1.0
calculator.CATEGORY_WEIGHTS['Analytics'] = 0.6
```

### Anomaly Detection Threshold

Adjust the anomaly detection threshold:

```python
from analytics import AnomalyDetector

# Default is 20% deviation
detector = AnomalyDetector(threshold=15.0)  # More sensitive
```

## Dependencies

- `reportlab`: PDF report generation
- `redis`: Caching layer
- `pydantic`: Data validation
- Standard library: `statistics`, `json`, `datetime`, `pathlib`

## Output Directories

By default, reports are saved to:
- `results/reports/` - Generated reports (PDF, HTML, JSON, CSV)

Ensure these directories exist or they will be created automatically.

## Performance Considerations

1. **Caching**: All metrics and trend calculations are cached in Redis with appropriate TTLs
2. **Batch Processing**: Use `warm_cache()` to pre-compute metrics for multiple scans
3. **Invalidation**: Cache is automatically invalidated when new scans are completed
4. **Report Generation**: PDF generation can be CPU-intensive for large datasets

## Error Handling

All components include comprehensive error handling and logging:

```python
import logging

# Enable debug logging for analytics
logging.getLogger('analytics').setLevel(logging.DEBUG)
```

## Testing

Test the analytics module:

```python
# Test metrics calculation
from analytics import MetricsCalculator
from models.scan import ScanResult

calculator = MetricsCalculator()
# ... create test scan result
metrics = calculator.calculate_comprehensive_metrics(test_scan)
assert 0 <= metrics.compliance_score <= 100

# Test caching
from analytics import AnalyticsCacheManager
cache_manager = AnalyticsCacheManager()
cache_manager.cache_metrics(scan_id, metrics)
cached = cache_manager.get_cached_metrics(scan_id)
assert cached is not None
```
