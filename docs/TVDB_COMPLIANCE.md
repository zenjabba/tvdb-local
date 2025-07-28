# TVDB v4 API Compliance

This proxy is designed to be a drop-in replacement for the official TVDB v4 API. Any application that works with TVDB's API can use this proxy by simply changing the base URL.

## Key Features

### 1. Full Authentication Compatibility

The proxy implements TVDB v4's authentication system exactly:

```bash
# TVDB Official
curl -X POST https://api4.thetvdb.com/v4/login \
  -H "Content-Type: application/json" \
  -d '{"apikey": "your-key", "pin": "optional-pin"}'

# This Proxy (identical request)
curl -X POST http://your-proxy-url/login \
  -H "Content-Type: application/json" \
  -d '{"apikey": "your-key", "pin": "optional-pin"}'
```

**Response Format (TVDB-compliant):**
```json
{
  "data": {
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  },
  "status": "success"
}
```

### 2. API Key Types

The proxy supports both TVDB API key types:

1. **Licensed Keys** (Company/Project keys)
   - No PIN required
   - Higher rate limits
   - For applications with TVDB contracts

2. **User-Supported Keys** 
   - Require user PIN
   - Lower rate limits
   - For open-source/community projects

### 3. Token Usage

Tokens work exactly like TVDB:
- Valid for 1 month
- Used as Bearer tokens in Authorization header
- Same format: `Authorization: Bearer [token]`

### 4. Endpoint Compatibility

All TVDB v4 endpoints are available at the same paths:
- `/v4/series/{id}`
- `/v4/movies/{id}`
- `/v4/episodes/{id}`
- `/v4/people/{id}`
- `/v4/search/*`

## Configuration for Applications

To use this proxy with any TVDB application:

### 1. Update Base URL

```python
# Original TVDB client
client = TVDBClient(
    base_url="https://api4.thetvdb.com",
    api_key="your-key"
)

# Using this proxy
client = TVDBClient(
    base_url="http://your-proxy-url",  # Only change needed!
    api_key="your-key"
)
```

### 2. No Code Changes Required

The proxy mimics TVDB's API exactly, so:
- Same authentication flow
- Same request/response formats
- Same error codes
- Same rate limiting headers

## Managing API Keys

This proxy issues its own API keys while using your system's TVDB credentials internally:

### Creating API Keys

```bash
# Create a licensed key (no PIN)
curl -X POST http://your-proxy/api/v1/admin/api-keys \
  -H "Authorization: Bearer admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My App",
    "rate_limit": 100,
    "requires_pin": false
  }'

# Create a user-supported key (with PIN)
curl -X POST http://your-proxy/api/v1/admin/api-keys \
  -H "Authorization: Bearer admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Community App",
    "rate_limit": 50,
    "requires_pin": true,
    "pin": "user-pin-here"
  }'
```

## Benefits Over Direct TVDB Access

1. **Caching**: Reduces load on TVDB and improves response times
2. **Rate Limiting**: Protects your TVDB API quota
3. **Monitoring**: Track usage per client
4. **Custom Keys**: Issue your own API keys to users
5. **High Availability**: Redis caching provides resilience

## Testing Compliance

Run the included test script:

```bash
python test_tvdb_compliance.py
```

This verifies:
- Login endpoint compatibility
- Token format and validity
- Authenticated request handling
- PIN-based authentication

## Example: Popular TVDB Libraries

### Python (tvdb_v4_official)
```python
from tvdb_v4_official import TVDB

# Just change the base URL in the library
tvdb = TVDB("your-proxy-key")
# Internally update: self.base_url = "http://your-proxy-url"
```

### JavaScript/Node
```javascript
const TVDB = require('node-tvdb');
const client = new TVDB('your-proxy-key', {
    baseURL: 'http://your-proxy-url'  // Instead of api4.thetvdb.com
});
```

### Any HTTP Client
```bash
# Get token
TOKEN=$(curl -s -X POST http://your-proxy/login \
  -H "Content-Type: application/json" \
  -d '{"apikey": "your-key"}' | jq -r .data.token)

# Use token
curl http://your-proxy/v4/series/121361 \
  -H "Authorization: Bearer $TOKEN"
```

## Environment Variables

Configure your proxy's TVDB credentials:
```env
TVDB_API_KEY=your-tvdb-api-key
TVDB_PIN=your-tvdb-pin  # Optional
```

The proxy uses these to communicate with the real TVDB API while your users authenticate with the keys you issue.