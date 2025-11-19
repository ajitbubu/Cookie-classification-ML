#!/usr/bin/env python3
"""
Test script for Three-Tier Scanning System

This script tests all three scanning tiers:
1. Quick Scan (ad-hoc)
2. Deep Scan (ad-hoc)
3. Scheduled Scan (automated)

Usage:
    python scripts/test_three_tier_system.py --api-url http://localhost:8000 --token YOUR_TOKEN
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta
from uuid import uuid4
import requests
from typing import Dict, Any, Optional


class ThreeTierTester:
    """Test harness for three-tier scanning system."""

    def __init__(self, api_url: str, token: Optional[str] = None):
        """Initialize tester with API URL and optional auth token."""
        self.api_url = api_url.rstrip('/')
        self.headers = {
            'Content-Type': 'application/json'
        }
        if token:
            self.headers['Authorization'] = f'Bearer {token}'

        self.test_domain = "https://example.com"
        self.test_domain_config_id = str(uuid4())
        self.created_schedule_ids = []

    def print_section(self, title: str):
        """Print formatted section header."""
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")

    def print_result(self, success: bool, message: str):
        """Print test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {message}")

    def test_tier1_quick_scan(self) -> bool:
        """Test Tier 1: Quick Scan (ad-hoc)."""
        self.print_section("TIER 1: Quick Scan Test")

        try:
            # Test quick scan endpoint
            payload = {
                "domain": self.test_domain,
                "custom_pages": ["/about", "/contact", "/privacy"],
                "max_concurrent": 5
            }

            print(f"Testing quick scan for {self.test_domain}...")
            print(f"Request: POST {self.api_url}/api/v1/parallel-scan/scan")
            print(f"Payload: {json.dumps(payload, indent=2)}\n")

            # Note: This will actually try to scan, so we'll just validate the request
            response = requests.post(
                f"{self.api_url}/api/v1/parallel-scan/scan",
                headers=self.headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                print(f"Response: {json.dumps(result, indent=2)[:500]}...\n")

                self.print_result(True, f"Quick scan completed")
                self.print_result(True, f"Pages scanned: {result.get('pages_scanned', 'N/A')}")
                self.print_result(True, f"Cookies found: {result.get('cookies_found', 'N/A')}")
                self.print_result(True, f"Duration: {result.get('scan_duration', 'N/A')}s")
                return True
            else:
                self.print_result(False, f"HTTP {response.status_code}: {response.text[:200]}")
                return False

        except requests.exceptions.ConnectionError:
            self.print_result(False, "Connection refused - is the API server running?")
            return False
        except Exception as e:
            self.print_result(False, f"Error: {str(e)}")
            return False

    def test_tier2_deep_scan(self) -> bool:
        """Test Tier 2: Deep Scan (ad-hoc)."""
        self.print_section("TIER 2: Deep Scan Test")

        try:
            # Test enterprise deep scan endpoint
            payload = {
                "domain": self.test_domain,
                "max_pages": 100,  # Small number for testing
                "browser_pool_size": 3,
                "pages_per_browser": 10,
                "chunk_size": 50
            }

            print(f"Testing deep scan for {self.test_domain}...")
            print(f"Request: POST {self.api_url}/api/v1/parallel-scan/enterprise/scan")
            print(f"Payload: {json.dumps(payload, indent=2)}\n")

            response = requests.post(
                f"{self.api_url}/api/v1/parallel-scan/enterprise/scan",
                headers=self.headers,
                json=payload,
                timeout=300  # 5 minutes
            )

            if response.status_code == 200:
                result = response.json()
                print(f"Response: {json.dumps(result, indent=2)[:500]}...\n")

                self.print_result(True, f"Deep scan completed")
                self.print_result(True, f"Total pages scanned: {result.get('total_pages_scanned', 'N/A')}")
                self.print_result(True, f"Unique cookies: {result.get('unique_cookies', 'N/A')}")
                self.print_result(True, f"Duration: {result.get('duration', 'N/A')}s")
                self.print_result(True, f"Pages/second: {result.get('pages_per_second', 'N/A')}")
                return True
            else:
                self.print_result(False, f"HTTP {response.status_code}: {response.text[:200]}")
                return False

        except requests.exceptions.ConnectionError:
            self.print_result(False, "Connection refused - is the API server running?")
            return False
        except Exception as e:
            self.print_result(False, f"Error: {str(e)}")
            return False

    def test_tier3_scheduled_scan(self) -> bool:
        """Test Tier 3: Scheduled Scan (automated)."""
        self.print_section("TIER 3: Scheduled Scan Test")

        success_count = 0
        total_tests = 6

        # Test 1: Create quick scheduled scan
        try:
            payload = {
                "domain_config_id": self.test_domain_config_id,
                "domain": self.test_domain,
                "scan_type": "quick",
                "scan_params": {
                    "custom_pages": ["/about", "/privacy"]
                },
                "frequency": "daily",
                "time_config": {
                    "hour": 9,
                    "minute": 0
                },
                "enabled": True
            }

            print("Test 1: Create quick scheduled scan")
            print(f"Request: POST {self.api_url}/api/v1/schedules")
            print(f"Payload: {json.dumps(payload, indent=2)}\n")

            response = requests.post(
                f"{self.api_url}/api/v1/schedules",
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code == 201:
                result = response.json()
                schedule_id = result['schedule_id']
                self.created_schedule_ids.append(schedule_id)

                self.print_result(True, f"Created quick schedule: {schedule_id}")
                self.print_result(True, f"Scan type: {result['scan_type']}")
                self.print_result(True, f"Frequency: {result['frequency']}")
                success_count += 1
            else:
                self.print_result(False, f"HTTP {response.status_code}: {response.text[:200]}")

        except Exception as e:
            self.print_result(False, f"Error creating quick schedule: {str(e)}")

        # Test 2: Create deep scheduled scan
        try:
            payload = {
                "domain_config_id": self.test_domain_config_id,
                "domain": self.test_domain,
                "scan_type": "deep",
                "scan_params": {
                    "max_pages": 5000,
                    "chunk_size": 1000
                },
                "frequency": "weekly",
                "time_config": {
                    "day_of_week": "monday",
                    "hour": 2,
                    "minute": 0
                },
                "enabled": True
            }

            print("\nTest 2: Create deep scheduled scan")
            response = requests.post(
                f"{self.api_url}/api/v1/schedules",
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code == 201:
                result = response.json()
                schedule_id = result['schedule_id']
                self.created_schedule_ids.append(schedule_id)

                self.print_result(True, f"Created deep schedule: {schedule_id}")
                self.print_result(True, f"Max pages: {result['scan_params'].get('max_pages', 'N/A')}")
                success_count += 1
            else:
                self.print_result(False, f"HTTP {response.status_code}: {response.text[:200]}")

        except Exception as e:
            self.print_result(False, f"Error creating deep schedule: {str(e)}")

        # Test 3: List schedules
        try:
            print("\nTest 3: List all schedules")
            response = requests.get(
                f"{self.api_url}/api/v1/schedules",
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                self.print_result(True, f"Retrieved {result['total']} schedules")
                self.print_result(True, f"Page {result['page']} of {result['total'] // result['page_size'] + 1}")
                success_count += 1
            else:
                self.print_result(False, f"HTTP {response.status_code}")

        except Exception as e:
            self.print_result(False, f"Error listing schedules: {str(e)}")

        # Test 4: Get specific schedule
        if self.created_schedule_ids:
            try:
                schedule_id = self.created_schedule_ids[0]
                print(f"\nTest 4: Get schedule {schedule_id}")
                response = requests.get(
                    f"{self.api_url}/api/v1/schedules/{schedule_id}",
                    headers=self.headers,
                    timeout=10
                )

                if response.status_code == 200:
                    result = response.json()
                    self.print_result(True, f"Retrieved schedule details")
                    self.print_result(True, f"Enabled: {result['enabled']}")
                    success_count += 1
                else:
                    self.print_result(False, f"HTTP {response.status_code}")

            except Exception as e:
                self.print_result(False, f"Error getting schedule: {str(e)}")

        # Test 5: Disable schedule
        if self.created_schedule_ids:
            try:
                schedule_id = self.created_schedule_ids[0]
                print(f"\nTest 5: Disable schedule {schedule_id}")
                response = requests.post(
                    f"{self.api_url}/api/v1/schedules/{schedule_id}/disable",
                    headers=self.headers,
                    timeout=10
                )

                if response.status_code == 200:
                    result = response.json()
                    self.print_result(True, f"Disabled schedule")
                    self.print_result(True, f"Enabled status: {result['enabled']}")
                    success_count += 1
                else:
                    self.print_result(False, f"HTTP {response.status_code}")

            except Exception as e:
                self.print_result(False, f"Error disabling schedule: {str(e)}")

        # Test 6: Enable schedule
        if self.created_schedule_ids:
            try:
                schedule_id = self.created_schedule_ids[0]
                print(f"\nTest 6: Enable schedule {schedule_id}")
                response = requests.post(
                    f"{self.api_url}/api/v1/schedules/{schedule_id}/enable",
                    headers=self.headers,
                    timeout=10
                )

                if response.status_code == 200:
                    result = response.json()
                    self.print_result(True, f"Enabled schedule")
                    self.print_result(True, f"Enabled status: {result['enabled']}")
                    success_count += 1
                else:
                    self.print_result(False, f"HTTP {response.status_code}")

            except Exception as e:
                self.print_result(False, f"Error enabling schedule: {str(e)}")

        print(f"\nSchedule API Tests: {success_count}/{total_tests} passed")
        return success_count == total_tests

    def cleanup(self):
        """Clean up test schedules."""
        self.print_section("Cleanup")

        for schedule_id in self.created_schedule_ids:
            try:
                response = requests.delete(
                    f"{self.api_url}/api/v1/schedules/{schedule_id}",
                    headers=self.headers,
                    timeout=10
                )

                if response.status_code == 204:
                    self.print_result(True, f"Deleted schedule {schedule_id}")
                else:
                    self.print_result(False, f"Failed to delete {schedule_id}: HTTP {response.status_code}")

            except Exception as e:
                self.print_result(False, f"Error deleting {schedule_id}: {str(e)}")

    def run_all_tests(self, skip_cleanup: bool = False):
        """Run all three-tier tests."""
        self.print_section("Three-Tier Scanning System Tests")

        print(f"API URL: {self.api_url}")
        print(f"Test Domain: {self.test_domain}")
        print(f"Auth: {'Enabled' if self.headers.get('Authorization') else 'Disabled'}")

        results = {
            'tier1_quick': False,
            'tier2_deep': False,
            'tier3_scheduled': False
        }

        # Run tests
        # results['tier1_quick'] = self.test_tier1_quick_scan()
        # results['tier2_deep'] = self.test_tier2_deep_scan()
        results['tier3_scheduled'] = self.test_tier3_scheduled_scan()

        # Cleanup
        if not skip_cleanup:
            self.cleanup()

        # Summary
        self.print_section("Test Summary")

        total = len(results)
        passed = sum(1 for v in results.values() if v)

        for tier, success in results.items():
            status = "✅" if success else "❌"
            print(f"{status} {tier.replace('_', ' ').title()}")

        print(f"\n{'='*80}")
        print(f"  OVERALL: {passed}/{total} tiers passed")
        print(f"{'='*80}\n")

        return passed == total


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Test Three-Tier Scanning System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with default settings (no auth)
  python scripts/test_three_tier_system.py

  # Test with authentication token
  python scripts/test_three_tier_system.py --token YOUR_JWT_TOKEN

  # Test against production API
  python scripts/test_three_tier_system.py --api-url https://api.example.com --token TOKEN

  # Skip cleanup (keep test schedules)
  python scripts/test_three_tier_system.py --skip-cleanup
        """
    )

    parser.add_argument(
        '--api-url',
        default='http://localhost:8000',
        help='API base URL (default: http://localhost:8000)'
    )

    parser.add_argument(
        '--token',
        help='Authentication token (JWT)'
    )

    parser.add_argument(
        '--skip-cleanup',
        action='store_true',
        help='Skip cleanup of test schedules'
    )

    args = parser.parse_args()

    # Run tests
    tester = ThreeTierTester(args.api_url, args.token)
    success = tester.run_all_tests(skip_cleanup=args.skip_cleanup)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
