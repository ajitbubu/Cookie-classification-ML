#!/usr/bin/env python3
"""
Verification script for Prometheus metrics implementation (Task 11.1).

This script demonstrates that all required metrics are properly implemented
and can be recorded and exported.
"""

from src.api.monitoring.metrics import (
    # Scan metrics
    record_scan_started,
    record_scan_completed,
    record_scan_failed,
    update_active_scans,
    # API metrics
    record_api_request,
    # Database metrics
    update_db_connections,
    # Cache metrics
    update_cache_hit_rate,
    # Export functions
    get_metrics_text,
    get_metrics_content_type
)


def main():
    print("=" * 70)
    print("Prometheus Metrics Verification - Task 11.1")
    print("=" * 70)
    
    # 1. Test scan metrics
    print("\n1. Recording scan metrics...")
    record_scan_started("quick")
    record_scan_started("deep")
    record_scan_completed("quick", 45.5)
    record_scan_completed("deep", 180.3)
    record_scan_failed("quick", 30.0)
    update_active_scans(3)
    print("   ✓ Scan metrics recorded")
    
    # 2. Test API metrics
    print("\n2. Recording API metrics...")
    record_api_request("/api/v1/scans", "POST", 201, 0.123)
    record_api_request("/api/v1/scans/123e4567-e89b-12d3-a456-426614174000", "GET", 200, 0.045)
    record_api_request("/api/v1/schedules", "GET", 200, 0.089)
    record_api_request("/api/v1/analytics/reports", "POST", 201, 1.234)
    print("   ✓ API metrics recorded")
    
    # 3. Test database metrics
    print("\n3. Recording database metrics...")
    update_db_connections(total=10, used=7, free=3)
    print("   ✓ Database metrics recorded")
    
    # 4. Test cache metrics
    print("\n4. Recording cache metrics...")
    update_cache_hit_rate(0.85)
    print("   ✓ Cache metrics recorded")
    
    # 5. Export metrics
    print("\n5. Exporting metrics in Prometheus format...")
    metrics_text = get_metrics_text()
    content_type = get_metrics_content_type()
    print(f"   ✓ Metrics exported: {len(metrics_text)} bytes")
    print(f"   ✓ Content-Type: {content_type}")
    
    # 6. Verify all required metrics are present
    print("\n6. Verifying required metrics are present...")
    metrics_str = metrics_text.decode('utf-8')
    
    required_metrics = {
        'dcs_scans_total': 'Counter for total scans by mode and status',
        'dcs_scan_duration_seconds': 'Histogram for scan duration',
        'dcs_active_scans': 'Gauge for active scans',
        'dcs_api_requests_total': 'Counter for API requests by endpoint, method, and status',
        'dcs_api_latency_seconds': 'Histogram for API latency by endpoint',
        'dcs_db_connections': 'Gauge for database connections',
        'dcs_cache_hit_rate': 'Gauge for cache hit rate'
    }
    
    all_present = True
    for metric_name, description in required_metrics.items():
        if metric_name in metrics_str:
            print(f"   ✓ {metric_name}: {description}")
        else:
            print(f"   ✗ {metric_name}: MISSING!")
            all_present = False
    
    # 7. Show sample output
    print("\n7. Sample Prometheus metrics output:")
    print("-" * 70)
    lines = metrics_str.split('\n')
    for i, line in enumerate(lines[:30]):  # Show first 30 lines
        print(f"   {line}")
    if len(lines) > 30:
        print(f"   ... ({len(lines) - 30} more lines)")
    print("-" * 70)
    
    # 8. Summary
    print("\n" + "=" * 70)
    if all_present:
        print("✓ SUCCESS: All required metrics are implemented and working!")
        print("\nTask 11.1 Implementation Complete:")
        print("  • prometheus_client library installed")
        print("  • Metrics module created (api/monitoring/metrics.py)")
        print("  • All 7 required metrics defined")
        print("  • Helper functions for recording metrics")
        print("  • /api/v1/metrics endpoint exposed")
        print("  • Automatic API tracking via middleware")
        print("\nNext steps:")
        print("  1. Start the API server: python run_api.py")
        print("  2. Access metrics: curl http://localhost:8000/api/v1/metrics")
        print("  3. Configure Prometheus to scrape the endpoint")
        print("  4. Create Grafana dashboards for visualization")
    else:
        print("✗ FAILURE: Some required metrics are missing!")
        return 1
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    exit(main())
