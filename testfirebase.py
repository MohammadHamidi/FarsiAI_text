#!/usr/bin/env python3
"""
Test script to verify Firebase integration works locally
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from firebase_utils import initialize_firebase, track_event
from config import settings

async def test_firebase():
    """Test Firebase initialization and event tracking"""
    
    print("🔥 Testing Firebase Integration")
    print("=" * 50)
    
    # Test 1: Configuration Check
    print(f"Firebase Analytics Enabled: {settings.FIREBASE_ANALYTICS_ENABLED}")
    print(f"Service Account Key Path: {settings.FIREBASE_SERVICE_ACCOUNT_KEY_PATH}")
    print(f"GA Measurement ID: {settings.GA_MEASUREMENT_ID}")
    print(f"GA API Secret: {'Set' if settings.GA_API_SECRET else 'Not Set'}")
    print(f"Project ID: docright-2e27b")
    print()
    
    # Test 2: Check if service account file exists
    if settings.FIREBASE_SERVICE_ACCOUNT_KEY_PATH:
        if os.path.exists(settings.FIREBASE_SERVICE_ACCOUNT_KEY_PATH):
            print("✅ Service account key file found")
        else:
            print("❌ Service account key file NOT found")
            print(f"Expected path: {settings.FIREBASE_SERVICE_ACCOUNT_KEY_PATH}")
            return
    
    # Test 3: Initialize Firebase
    try:
        initialize_firebase()
        print("✅ Firebase initialized successfully")
    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")
        return
    
    # Test 4: Test event tracking
    try:
        await track_event(
            "test_event", 
            {
                "test_parameter": "local_test",
                "timestamp": "2025-05-29"
            },
            user_ip="127.0.0.1",
            user_agent="Test-Agent/1.0"
        )
        print("✅ Test event sent successfully")
        print("Check your GA4 Realtime reports to see the event")
    except Exception as e:
        print(f"❌ Event tracking failed: {e}")
    
    print("\n🎉 Firebase test completed!")
    print("If all tests passed, Firebase is ready for production deployment.")

if __name__ == "__main__":
    asyncio.run(test_firebase())