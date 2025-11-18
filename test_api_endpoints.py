"""
Integration tests for API endpoints (Task 6).
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Mock test to verify endpoint structure
def test_analytics_endpoints_exist():
    """Test that analytics endpoints are properly defined."""
    try:
        from api.routers import analytics
        
        # Check router exists
        assert analytics.router is not None
        
        # Check routes are registered
        routes = [route.path for route in analytics.router.routes]
        
        # Verify expected endpoints
        assert "/reports/{scan_id}" in routes
        assert "/reports" in routes
        assert "/trends" in routes
        assert "/metrics" in routes
        
        print("✓ Analytics endpoints properly defined")
        return True
    except ImportError as e:
        print(f"✗ Failed to import analytics router: {e}")
        return False


def test_health_endpoints_exist():
    """Test that health endpoints are properly defined."""
    try:
        from api.routers import health
        
        # Check router exists
        assert health.router is not None
        
        # Check routes are registered
        routes = [route.path for route in health.router.routes]
        
        # Verify expected endpoints
        assert "/health" in routes
        assert "/metrics" in routes
        assert "/ready" in routes
        assert "/live" in routes
        
        print("✓ Health endpoints properly defined")
        return True
    except ImportError as e:
        print(f"✗ Failed to import health router: {e}")
        return False


def test_notification_endpoints_exist():
    """Test that notification endpoints are properly defined."""
    try:
        from api.routers import notifications
        
        # Check router exists
        assert notifications.router is not None
        
        # Check routes are registered
        routes = [route.path for route in notifications.router.routes]
        
        # Verify expected endpoints
        assert "/preferences" in routes
        assert "/history" in routes
        assert "/events" in routes
        assert "/channels" in routes
        
        print("✓ Notification endpoints properly defined")
        return True
    except ImportError as e:
        print(f"✗ Failed to import notifications router: {e}")
        return False


def test_profile_endpoints_exist():
    """Test that profile endpoints are properly defined."""
    try:
        from api.routers import profiles
        
        # Check router exists
        assert profiles.router is not None
        
        # Check routes are registered
        routes = [route.path for route in profiles.router.routes]
        
        # Verify expected endpoints
        assert "" in routes  # List/Create
        assert "/{profile_id}" in routes  # Get/Update/Delete
        
        print("✓ Profile endpoints properly defined")
        return True
    except ImportError as e:
        print(f"✗ Failed to import profiles router: {e}")
        return False


def test_services_exist():
    """Test that required services are properly defined."""
    try:
        from services.analytics_service import AnalyticsService
        from services.health_checker import HealthChecker
        
        # Check services can be imported
        assert AnalyticsService is not None
        assert HealthChecker is not None
        
        print("✓ Required services properly defined")
        return True
    except ImportError as e:
        print(f"✗ Failed to import services: {e}")
        return False


def test_analytics_service_methods():
    """Test that AnalyticsService has required methods."""
    try:
        from services.analytics_service import AnalyticsService
        
        # Check methods exist
        assert hasattr(AnalyticsService, 'get_scan_result')
        assert hasattr(AnalyticsService, 'list_scan_results')
        assert hasattr(AnalyticsService, 'generate_report')
        assert hasattr(AnalyticsService, 'get_trend_data')
        assert hasattr(AnalyticsService, 'get_metrics_summary')
        
        print("✓ AnalyticsService has all required methods")
        return True
    except ImportError as e:
        print(f"✗ Failed to import AnalyticsService: {e}")
        return False


def test_health_checker_methods():
    """Test that HealthChecker has required methods."""
    try:
        from services.health_checker import HealthChecker
        
        # Check methods exist
        assert hasattr(HealthChecker, 'check_health')
        assert hasattr(HealthChecker, 'check_database')
        assert hasattr(HealthChecker, 'check_redis')
        assert hasattr(HealthChecker, 'check_browser')
        assert hasattr(HealthChecker, 'check_scheduler')
        assert hasattr(HealthChecker, 'get_metrics')
        
        print("✓ HealthChecker has all required methods")
        return True
    except ImportError as e:
        print(f"✗ Failed to import HealthChecker: {e}")
        return False


if __name__ == "__main__":
    print("\n=== Running Task 6 API Endpoint Tests ===\n")
    
    results = []
    results.append(test_analytics_endpoints_exist())
    results.append(test_health_endpoints_exist())
    results.append(test_notification_endpoints_exist())
    results.append(test_profile_endpoints_exist())
    results.append(test_services_exist())
    results.append(test_analytics_service_methods())
    results.append(test_health_checker_methods())
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n=== Test Results: {passed}/{total} passed ===\n")
    
    if passed == total:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed. Please check the output above.")
        sys.exit(1)
