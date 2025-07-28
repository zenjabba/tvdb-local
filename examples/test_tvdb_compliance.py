#!/usr/bin/env python3
"""Test script to verify TVDB v4 API compliance"""
import requests
import json

# Configuration
PROXY_URL = "http://localhost:8888"  # Your proxy
TVDB_URL = "https://api4.thetvdb.com"  # Official TVDB

# Test credentials (update these with your actual keys)
API_KEY = "tvdb-demo-user-key"
PIN = "1234"


def test_login(base_url, api_key, pin=None):
    """Test TVDB-compliant login"""
    print(f"\nTesting login at {base_url}/login")

    payload = {"apikey": api_key}
    if pin:
        payload["pin"] = pin

    response = requests.post(
        f"{base_url}/login",
        json=payload,
        headers={"Content-Type": "application/json"}
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    if response.status_code == 200:
        token = response.json().get("data", {}).get("token")
        print(f"Login successful! Token: {token[:20]}...")
        return token
    else:
        print("Login failed!")
        return None


def test_authenticated_request(base_url, token, endpoint):
    """Test authenticated API request"""
    print(f"\nTesting authenticated request to {base_url}{endpoint}")

    response = requests.get(
        f"{base_url}{endpoint}",
        headers={"Authorization": f"Bearer {token}"}
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("Authenticated request successful!")
        # Don't print full response as it might be large
        data = response.json()
        if isinstance(data, dict) and "data" in data:
            print(f"Response contains {len(data.get('data', []))} items")
    else:
        print(f"Request failed: {response.text}")


def main():
    """Run TVDB compliance tests"""
    print("=== TVDB v4 API Compliance Test ===")

    # Test 1: Login without PIN (should work for non-PIN keys)
    print("\n1. Testing login without PIN:")
    token = test_login(PROXY_URL, "demo-key-1")

    # Test 2: Login with PIN required key without PIN (should fail)
    print("\n2. Testing PIN-required key without PIN (should fail):")
    test_login(PROXY_URL, API_KEY)

    # Test 3: Login with PIN
    print("\n3. Testing login with PIN:")
    token_with_pin = test_login(PROXY_URL, API_KEY, PIN)

    # Test 4: Make authenticated requests
    if token:
        print("\n4. Testing authenticated requests:")
        test_authenticated_request(PROXY_URL, token, "/v4/series/121361")  # Game of Thrones
        test_authenticated_request(PROXY_URL, token, "/v4/search/series?q=breaking")

    print("\n=== Compliance Test Complete ===")
    print("\nTo test against real TVDB API:")
    print("1. Replace API_KEY with your TVDB API key")
    print("2. Uncomment the line below and run again")
    # test_login(TVDB_URL, "your-real-tvdb-key", "your-pin-if-needed")


if __name__ == "__main__":
    main()
