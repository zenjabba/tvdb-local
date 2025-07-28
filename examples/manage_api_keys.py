#!/usr/bin/env python3
"""
Example: Managing API Keys in TVDB Proxy

This script demonstrates how to:
1. Create user-supported keys (with PIN)
2. Create licensed keys (without PIN)
3. List all API keys
4. Update API key settings
"""

import requests
import json
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8888"
ADMIN_API_KEY = "admin-super-key-change-in-production"


def get_admin_token() -> str:
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/login",
        json={"apikey": ADMIN_API_KEY}
    )
    response.raise_for_status()
    return response.json()["data"]["token"]


def create_api_key(
    token: str,
    name: str,
    description: str,
    rate_limit: int = 100,
    requires_pin: bool = False,
    pin: Optional[str] = None
) -> dict:
    """Create a new API key"""
    payload = {
        "name": name,
        "description": description,
        "rate_limit": rate_limit,
        "requires_pin": requires_pin
    }
    
    if requires_pin and pin:
        payload["pin"] = pin
    
    response = requests.post(
        f"{BASE_URL}/api/v1/admin/api-keys",
        headers={"Authorization": f"Bearer {token}"},
        json=payload
    )
    response.raise_for_status()
    return response.json()


def list_api_keys(token: str) -> list:
    """List all API keys"""
    response = requests.get(
        f"{BASE_URL}/api/v1/admin/api-keys",
        headers={"Authorization": f"Bearer {token}"}
    )
    response.raise_for_status()
    return response.json()["keys"]


def main():
    print("=== TVDB Proxy API Key Management ===\n")
    
    # Get admin token
    print("1. Getting admin token...")
    admin_token = get_admin_token()
    print("Admin authenticated\n")
    
    # Create a licensed key (no PIN)
    print("2. Creating licensed API key (no PIN required)...")
    licensed_key = create_api_key(
        token=admin_token,
        name="My Company App",
        description="Licensed key for commercial application",
        rate_limit=200,
        requires_pin=False
    )
    print(f"Created: {licensed_key['name']}")
    print(f"   Key: {licensed_key['key']}")
    print(f"   Rate limit: {licensed_key['rate_limit']}/min\n")
    
    # Create a user-supported key (with PIN)
    print("3. Creating user-supported API key (PIN required)...")
    user_key = create_api_key(
        token=admin_token,
        name="Community Project",
        description="Open-source project requiring user subscription",
        rate_limit=50,
        requires_pin=True,
        pin="user123"
    )
    print(f"Created: {user_key['name']}")
    print(f"   Key: {user_key['key']}")
    print(f"   PIN: user123")
    print(f"   Rate limit: {user_key['rate_limit']}/min\n")
    
    # List all keys
    print("4. Listing all API keys...")
    keys = list_api_keys(admin_token)
    print(f"Total keys: {len(keys)}\n")
    
    for key in keys:
        pin_status = "PIN required" if key['requires_pin'] else "No PIN"
        print(f"   - {key['name']} ({pin_status})")
        print(f"     Rate limit: {key['rate_limit']}/min")
        print(f"     Active: {key['active']}")
        print(f"     Total requests: {key['total_requests']}")
        print()
    
    # Example: How users would authenticate
    print("=== User Authentication Examples ===\n")
    
    print("Licensed key (no PIN):")
    print(f"curl -X POST {BASE_URL}/login \\")
    print(f'  -H "Content-Type: application/json" \\')
    print(f'  -d \'{{"apikey": "{licensed_key["key"]}"}}\'\n')
    
    print("User-supported key (with PIN):")
    print(f"curl -X POST {BASE_URL}/login \\")
    print(f'  -H "Content-Type: application/json" \\')
    print(f'  -d \'{{"apikey": "{user_key["key"]}", "pin": "user123"}}\'\n')


if __name__ == "__main__":
    main()