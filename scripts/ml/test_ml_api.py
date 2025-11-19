#!/usr/bin/env python3
"""
Test ML Admin API Endpoints

Demonstrates usage of ML administration API endpoints.
Requires API to be running: uvicorn api.main:app
"""

import requests
import json
from typing import Dict, Any

# API Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
# Note: In production, you would need to authenticate first
# and include the token in headers: {"Authorization": f"Bearer {token}"}


def print_response(title: str, response: requests.Response):
    """Pretty print API response."""
    print("\n" + "=" * 70)
    print(f"{title}")
    print("=" * 70)
    print(f"Status: {response.status_code}")

    try:
        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2)}")
    except:
        print(f"Response: {response.text}")


def test_model_info():
    """Test GET /api/v1/ml/model-info endpoint."""
    print("\n📊 Testing Model Info Endpoint")

    try:
        response = requests.get(f"{API_BASE_URL}/ml/model-info")
        print_response("GET /api/v1/ml/model-info", response)

        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ Model Version: {data.get('model_version')}")
            print(f"✓ Model Type: {data.get('model_type')}")
            print(f"✓ Accuracy: {data.get('accuracy', 'N/A')}")
            print(f"✓ Categories: {', '.join(data.get('categories', []))}")
        elif response.status_code == 404:
            print("\n⚠ Model not found. Train a model first:")
            print("  python scripts/train_model.py")

    except requests.exceptions.ConnectionError:
        print("\n✗ Could not connect to API")
        print("  Start the API first: uvicorn api.main:app")
    except Exception as e:
        print(f"\n✗ Error: {e}")


def test_metrics():
    """Test GET /api/v1/ml/metrics endpoint."""
    print("\n📈 Testing Metrics Endpoint")

    try:
        response = requests.get(f"{API_BASE_URL}/ml/metrics")
        print_response("GET /api/v1/ml/metrics", response)

        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ Predictions Count: {data.get('predictions_count', 0)}")
            print(f"✓ Average Confidence: {data.get('avg_confidence', 0):.1%}")
            print(f"✓ Low Confidence Count: {data.get('low_confidence_count', 0)}")
            print(f"✓ Feedback Count: {data.get('feedback_count', 0)}")

    except requests.exceptions.ConnectionError:
        print("\n✗ Could not connect to API")
    except Exception as e:
        print(f"\n✗ Error: {e}")


def test_low_confidence_cookies():
    """Test GET /api/v1/ml/low-confidence endpoint."""
    print("\n🔍 Testing Low-Confidence Cookies Endpoint")

    try:
        params = {
            "limit": 10,
            "max_confidence": 0.75
        }
        response = requests.get(f"{API_BASE_URL}/ml/low-confidence", params=params)
        print_response("GET /api/v1/ml/low-confidence", response)

        if response.status_code == 200:
            cookies = response.json()
            print(f"\n✓ Found {len(cookies)} low-confidence cookies")

            if cookies:
                print("\nSample cookie:")
                cookie = cookies[0]
                print(f"  Name: {cookie.get('name')}")
                print(f"  Domain: {cookie.get('domain')}")
                print(f"  Predicted: {cookie.get('predicted_category')}")
                print(f"  Confidence: {cookie.get('ml_confidence', 0):.1%}")

    except requests.exceptions.ConnectionError:
        print("\n✗ Could not connect to API")
    except Exception as e:
        print(f"\n✗ Error: {e}")


def test_submit_feedback():
    """Test POST /api/v1/ml/feedback endpoint."""
    print("\n💬 Testing Feedback Submission Endpoint")

    try:
        feedback_data = {
            "cookie_name": "_test_cookie",
            "cookie_domain": ".example.com",
            "predicted_category": "Analytics",
            "correct_category": "Necessary",
            "ml_confidence": 0.45,
            "notes": "This is a test correction"
        }

        response = requests.post(
            f"{API_BASE_URL}/ml/feedback",
            json=feedback_data
        )
        print_response("POST /api/v1/ml/feedback", response)

        if response.status_code == 201:
            data = response.json()
            print(f"\n✓ Feedback submitted successfully")
            print(f"✓ Feedback ID: {data.get('feedback_id')}")
            print(f"✓ Added to training queue: {data.get('added_to_training_queue')}")

    except requests.exceptions.ConnectionError:
        print("\n✗ Could not connect to API")
    except Exception as e:
        print(f"\n✗ Error: {e}")


def test_training_queue():
    """Test GET /api/v1/ml/training-queue endpoint."""
    print("\n📋 Testing Training Queue Endpoint")

    try:
        response = requests.get(f"{API_BASE_URL}/ml/training-queue")
        print_response("GET /api/v1/ml/training-queue", response)

        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ Total Corrections: {data.get('total_corrections', 0)}")
            print(f"✓ Ready for Retraining: {data.get('ready_for_retraining', False)}")

            if data.get('corrections_by_category'):
                print(f"\nBreakdown by category:")
                for cat, count in data['corrections_by_category'].items():
                    print(f"  {cat}: {count}")

    except requests.exceptions.ConnectionError:
        print("\n✗ Could not connect to API")
    except Exception as e:
        print(f"\n✗ Error: {e}")


def main():
    """Run all API tests."""
    print("=" * 70)
    print("ML ADMIN API ENDPOINT TESTS")
    print("=" * 70)
    print("\nNote: This script assumes the API is running locally")
    print("Start API with: uvicorn api.main:app --reload")
    print("\n" + "=" * 70)

    # Test each endpoint
    test_model_info()
    test_metrics()
    test_low_confidence_cookies()
    test_training_queue()
    # test_submit_feedback()  # Commented out to avoid creating test data

    print("\n" + "=" * 70)
    print("TESTS COMPLETE")
    print("=" * 70)
    print("\nAPI Endpoints Available:")
    print("  GET  /api/v1/ml/model-info        - Model information")
    print("  GET  /api/v1/ml/metrics            - Performance metrics")
    print("  GET  /api/v1/ml/low-confidence     - Review queue")
    print("  POST /api/v1/ml/feedback           - Submit corrections")
    print("  POST /api/v1/ml/feedback/bulk      - Bulk corrections")
    print("  GET  /api/v1/ml/training-queue     - Training queue status")
    print("\nView API docs: http://localhost:8000/docs")
    print("=" * 70)


if __name__ == "__main__":
    main()
