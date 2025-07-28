# TVDB Proxy Examples

This directory contains example scripts and code samples for using the TVDB Proxy.

## Available Examples

### 1. test_tvdb_compliance.py
Test script to verify TVDB v4 API compliance.

**Usage:**
```bash
python3 test_tvdb_compliance.py
```

**What it tests:**
- Login endpoint (with and without PIN)
- Token format compliance
- Authenticated API requests
- Error handling

### 2. manage_api_keys.py
Comprehensive Python example for API key management.

**Usage:**
```bash
python3 manage_api_keys.py
```

**Features demonstrated:**
- Creating licensed keys (no PIN)
- Creating user-supported keys (with PIN)
- Listing all API keys
- Authentication examples

### 3. create_user_key.sh
Quick bash script to create a user-supported API key.

**Usage:**
```bash
./create_user_key.sh
```

**What it does:**
- Gets admin authentication token
- Creates a new user-supported key with PIN
- Shows the created key details

## Quick Examples

### Authenticate with Licensed Key
```bash
curl -X POST http://localhost:8888/login \
  -H "Content-Type: application/json" \
  -d '{"apikey": "demo-key-1"}'
```

### Authenticate with User-Supported Key
```bash
curl -X POST http://localhost:8888/login \
  -H "Content-Type: application/json" \
  -d '{"apikey": "tvdb-demo-user-key", "pin": "1234"}'
```

### Use Token for API Request
```bash
# Get token first
TOKEN=$(curl -s -X POST http://localhost:8888/login \
  -H "Content-Type: application/json" \
  -d '{"apikey": "demo-key-1"}' | jq -r .data.token)

# Make authenticated request
curl http://localhost:8888/v4/series/121361 \
  -H "Authorization: Bearer $TOKEN"
```

## Demo API Keys

The following demo keys are available after running `init_demo_keys.py`:

| Key | Type | PIN | Purpose |
|-----|------|-----|---------|
| `demo-key-1` | Licensed | - | Basic testing |
| `demo-key-2` | Licensed | - | Higher rate limit testing |
| `tvdb-demo-user-key` | User-supported | `1234` | PIN authentication testing |
| `admin-super-key-change-in-production` | Admin | - | API key management |

## Python Integration Example

```python
import requests

# Configuration
BASE_URL = "http://localhost:8888"
API_KEY = "demo-key-1"

# Get token
response = requests.post(
    f"{BASE_URL}/login",
    json={"apikey": API_KEY}
)
token = response.json()["data"]["token"]

# Use token for API requests
headers = {"Authorization": f"Bearer {token}"}
series = requests.get(
    f"{BASE_URL}/v4/series/121361",
    headers=headers
).json()

print(f"Series: {series['data']['name']}")
```