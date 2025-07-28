# TVDB Proxy

A high-performance caching proxy for TVDB API v4 with **database-backed API key management** and local data storage using Redis and PostgreSQL, protecting your API key and providing blazing-fast responses.

## Features

- 🚀 **Full TVDB v4 API Compatibility**: Drop-in replacement for api4.thetvdb.com
- 🔐 **Dual Authentication Modes**: Support for both licensed and user-supported (PIN-based) keys
- ⚡ **High Performance**: Redis caching with sub-100ms response times
- 🔑 **Database-Backed API Keys**: PostgreSQL-stored API keys with full CRUD management
- 📦 **Complete Data Storage**: PostgreSQL for persistent TVDB data and authentication
- 🔄 **Auto-Sync**: Background workers keep data up-to-date
- 🛡️ **Rate Limiting**: Configurable rate limiting per client
- 📊 **Usage Analytics**: Track API usage per client with real-time statistics
- 🐳 **Docker Ready**: Complete containerized deployment
- 📖 **Well Documented**: Comprehensive docs and examples

## Quick Start

### Docker Images

Pre-built Docker images are available on Docker Hub:
- API: `docker pull zenjabba/tvdb-local:latest`
- Worker: `docker pull zenjabba/tvdb-local-worker:latest`

### Prerequisites

- Docker and Docker Compose
- TVDB API key from [thetvdb.com](https://thetvdb.com)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd tvdb-proxy
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file with your TVDB API key:

```env
TVDB_API_KEY=your_tvdb_api_key_here
TVDB_PIN=your_optional_pin_here
SECRET_KEY=generate_a_secure_secret_key
```

### 3. Start Services

```bash
docker-compose up -d
```

The API will be available at `http://localhost:8888`

### 4. Initialize Demo Keys

```bash
docker-compose exec -T api python -m scripts.init_demo_keys
```

### 5. Health Check

```bash
curl http://localhost:8888/health
```

## TVDB v4 API Compliance

This proxy is a **drop-in replacement** for the official TVDB v4 API. Any application that works with TVDB can use this proxy by simply changing the base URL from `https://api4.thetvdb.com` to `http://localhost:8888`.

### Authentication (TVDB v4 Compatible)

```bash
# Licensed key (no PIN required)
curl -X POST "http://localhost:8888/login" \
  -H "Content-Type: application/json" \
  -d '{"apikey": "demo-key-1"}'

# User-supported key (PIN required)
curl -X POST "http://localhost:8888/login" \
  -H "Content-Type: application/json" \
  -d '{"apikey": "tvdb-demo-user-key", "pin": "1234"}'
```

Response (TVDB v4 format):
```json
{
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs..."
  },
  "status": "success"
}
```

Use the token in subsequent requests (exactly like TVDB):

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8888/v4/series/121361"
```

## API Key Types

The proxy supports both TVDB API key types:

### 1. Licensed Keys (No PIN Required)
- For commercial applications with TVDB contracts
- Higher rate limits
- Example: `demo-key-1`, `demo-key-2`

### 2. User-Supported Keys (PIN Required)
- For open-source/community projects
- Requires user's TVDB subscription PIN
- Example: `tvdb-demo-user-key` (PIN: `1234`)

### Default Demo Keys

| Key | Type | PIN | Rate Limit |
|-----|------|-----|------------|
| `demo-key-1` | Licensed | None | 100/min |
| `demo-key-2` | Licensed | None | 200/min |
| `tvdb-demo-user-key` | User-supported | `1234` | 50/min |
| `admin-super-key-change-in-production` | Admin | None | 1000/min |

### Endpoints

#### Series

```bash
# Get series by ID
GET /v4/series/{series_id}

# Get extended series information  
GET /v4/series/{series_id}?extended=true

# Get series episodes
GET /v4/series/{series_id}/episodes?page=0

# Get all series (paginated)
GET /v4/series?page=0
```

#### Movies

```bash
# Get movie by ID
GET /v4/movies/{movie_id}

# Get extended movie information
GET /v4/movies/{movie_id}?extended=true
```

#### Episodes

```bash
# Get episode by ID
GET /v4/episodes/{episode_id}
```

#### People

```bash
# Get person by ID
GET /v4/people/{person_id}
```

#### Search

```bash
# Search series
GET /v4/search/series?q=breaking+bad

# Search movies
GET /v4/search/movies?q=inception

# Search people
GET /v4/search/people?q=bryan+cranston

# Search all types
GET /v4/search/all?q=batman
```

## Using with TVDB Applications

To use this proxy with any TVDB application, simply change the base URL:

### Python (tvdb_v4_official)
```python
from tvdb_v4_official import TVDB

# Original
tvdb = TVDB("your-api-key")
# Internally: base_url="https://api4.thetvdb.com"

# Using proxy
tvdb = TVDB("your-api-key")
tvdb.base_url = "http://localhost:8888"  # Override base URL
```

### JavaScript/Node
```javascript
const TVDB = require('node-tvdb');

// Using proxy  
const client = new TVDB('your-api-key', {
    baseURL: 'http://localhost:8888'  // Instead of api4.thetvdb.com
});
```

### Any HTTP Client
```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8888/login \
  -H "Content-Type: application/json" \
  -d '{"apikey": "your-key"}' | jq -r .data.token)

# Use token
curl http://localhost:8888/v4/series/121361 \
  -H "Authorization: Bearer $TOKEN"
```

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   Client App    │    │  TVDB Proxy  │    │ TVDB API v4 │
│                 │───▶│   (FastAPI)  │───▶│             │
│                 │    │              │    │             │
└─────────────────┘    └──────────────┘    └─────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │    Redis     │
                       │   (Cache)    │
                       └──────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │ PostgreSQL   │
                       │ (Persistent) │
                       └──────────────┘
```

### Components

- **API Gateway**: FastAPI application with database-backed authentication and rate limiting
- **Redis**: Fast caching layer for frequently accessed TVDB data
- **PostgreSQL**: Primary database for API keys, user management, and persistent TVDB data
- **Celery Workers**: Background synchronization and cache management
- **TVDB Client**: Enhanced wrapper around official Python library

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TVDB_API_KEY` | Your TVDB API key | Required |
| `TVDB_PIN` | Optional TVDB PIN | None |
| `DATABASE_URL` | PostgreSQL connection string | See .env.example |
| `REDIS_URL` | Redis connection string | redis://redis:6379/0 |
| `SECRET_KEY` | JWT signing secret | Required |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | Rate limit per minute | 100 |
| `SYNC_INTERVAL_MINUTES` | Sync frequency | 15 |
| `CACHE_TTL_STATIC_HOURS` | Static data cache TTL | 24 |
| `CACHE_TTL_DYNAMIC_HOURS` | Dynamic data cache TTL | 1 |

## Database Migration Complete ✅

**The TVDB Proxy has been migrated to use full database storage for API key management.**

### What's New
- **PostgreSQL Storage**: All API keys are now stored in the database (no more config files)
- **Admin REST API**: Full CRUD operations for API key management via HTTP endpoints
- **Usage Tracking**: Real-time request counting and statistics per key
- **Enhanced Security**: Database-backed authentication with audit trails
- **Key Rotation**: Secure API key rotation without service interruption

## API Key Management

### Overview

The TVDB Proxy uses a sophisticated database-backed API key management system to authenticate clients and control access. Each API key has configurable rate limits, usage tracking, and can be managed via REST API endpoints.

### Admin Authentication

To manage API keys, you need admin access using the super admin key:

```bash
# Default admin key (CHANGE IN PRODUCTION!)
ADMIN_KEY="admin-super-key-change-in-production"
```

### Creating New API Keys

Create new API keys via the admin REST API:

```bash
curl -X POST "http://localhost:8888/api/v1/admin/api-keys" \
  -H "Authorization: Bearer admin-super-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Client",
    "description": "Main production API client",
    "rate_limit": 500,
    "active": true
  }'
```

**Response** (includes the full API key only once):
```json
{
  "id": 4,
  "name": "Production Client",
  "description": "Main production API client",
  "active": true,
  "rate_limit": 500,
  "key_preview": "...xyz",
  "key": "api-abc123def456ghi789...",
  "total_requests": 0,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Managing Existing API Keys

#### List All API Keys

```bash
curl -H "Authorization: Bearer admin-super-key-change-in-production" \
  "http://localhost:8888/api/v1/admin/api-keys?page=1&per_page=20"
```

#### Get Specific API Key Details

```bash
curl -H "Authorization: Bearer admin-super-key-change-in-production" \
  "http://localhost:8888/api/v1/admin/api-keys/4"
```

#### Update API Key

```bash
curl -X PUT "http://localhost:8888/api/v1/admin/api-keys/4" \
  -H "Authorization: Bearer admin-super-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Client Name",
    "rate_limit": 1000,
    "active": true
  }'
```

#### Rotate API Key (Generate New Key)

```bash
curl -X POST "http://localhost:8888/api/v1/admin/api-keys/4/rotate" \
  -H "Authorization: Bearer admin-super-key-change-in-production"
```

#### Delete API Key

```bash
curl -X DELETE "http://localhost:8888/api/v1/admin/api-keys/4" \
  -H "Authorization: Bearer admin-super-key-change-in-production"
```

#### Get Usage Statistics

```bash
curl -H "Authorization: Bearer admin-super-key-change-in-production" \
  "http://localhost:8888/api/v1/admin/api-keys/stats/usage"
```

### API Key Configuration Options

Each API key supports the following configuration options:

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `name` | string | Human-readable client identifier | "Production App", "Mobile Client" |
| `description` | string | Optional description of the key's purpose | "Main production API client" |
| `rate_limit` | integer | Maximum requests per minute (1-10000) | 100, 500, 1000 |
| `active` | boolean | Whether the key is enabled | true, false |
| `expires_at` | datetime | Optional expiration date | "2024-12-31T23:59:59Z" |
| `created_by` | string | Admin who created the key | "admin", "john.doe" |

### API Key Features

- **Automatic Key Generation**: Cryptographically secure keys with `api-` prefix
- **Usage Tracking**: Tracks total requests and last used timestamp
- **Rate Limiting**: Per-key rate limits with configurable requests per minute
- **Expiration**: Optional key expiration dates
- **Security**: Keys are never fully displayed after creation (only preview)
- **Audit Trail**: Tracks creation date, creator, and usage statistics

### Example API Key Creation

```bash
# High-volume production client
curl -X POST "http://localhost:8888/api/v1/admin/api-keys" \
  -H "Authorization: Bearer admin-super-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production API Client",
    "description": "Main production client for web application",
    "rate_limit": 1000,
    "active": true
  }'

# Mobile app with moderate usage
curl -X POST "http://localhost:8888/api/v1/admin/api-keys" \
  -H "Authorization: Bearer admin-super-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mobile Application",
    "description": "iOS and Android mobile apps",
    "rate_limit": 200,
    "active": true
  }'

# Development/testing key with expiration
curl -X POST "http://localhost:8888/api/v1/admin/api-keys" \
  -H "Authorization: Bearer admin-super-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Development Environment",
    "description": "Temporary key for development testing",
    "rate_limit": 50,
    "active": true,
    "expires_at": "2024-12-31T23:59:59Z"
  }'
```

### Default Demo Keys

The system initializes with demo keys for testing (remove in production):

- `demo-key-1`: Demo Client 1, 100 requests/minute
- `demo-key-2`: Demo Client 2, 200 requests/minute  
- `admin-super-key-change-in-production`: Super Admin Key, 1000 requests/minute

Run the initialization script to create demo keys:

```bash
docker-compose exec api python scripts/init_demo_keys.py
```

### Rate Limiting Details

- **Per-Key Limits**: Each API key has its own configurable rate limit (1-10000 requests per minute)
- **Global Limits**: Additional global rate limiting configured via `RATE_LIMIT_REQUESTS_PER_MINUTE`
- **Burst Handling**: Short bursts above rate limit allowed via `RATE_LIMIT_BURST` setting
- **Usage Tracking**: Real-time tracking of request counts and last used timestamps
- **Rate Limit Headers**: API responses include rate limit headers for monitoring

### Production Best Practices

1. **Change Default Admin Key**:
```bash
# Create new admin key
curl -X POST "http://localhost:8888/api/v1/admin/api-keys" \
  -H "Authorization: Bearer admin-super-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Admin Key",
    "description": "Production administrative key",
    "rate_limit": 1000,
    "active": true
  }'

# Then disable or delete the default admin key
curl -X PUT "http://localhost:8888/api/v1/admin/api-keys/3" \
  -H "Authorization: Bearer your-new-admin-key" \
  -H "Content-Type: application/json" \
  -d '{"active": false}'
```

2. **Remove Demo Keys**:
```bash
# Disable demo keys
curl -X DELETE "http://localhost:8888/api/v1/admin/api-keys/1" \
  -H "Authorization: Bearer your-admin-key"
curl -X DELETE "http://localhost:8888/api/v1/admin/api-keys/2" \
  -H "Authorization: Bearer your-admin-key"
```

3. **Set Appropriate Rate Limits**:
- Start conservative (100-200 req/min) and increase as needed
- Monitor usage via admin endpoints and adjust accordingly
- Consider peak usage patterns and client requirements

4. **Key Naming Convention**:
```bash
# Use descriptive, environment-specific names
"Production Web Application"
"Mobile App - iOS"
"Development Environment"
"Integration Testing"
```

### Administrative Operations

**Disable a key temporarily**:
```bash
curl -X PUT "http://localhost:8888/api/v1/admin/api-keys/4" \
  -H "Authorization: Bearer admin-super-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{"active": false}'
```

**Monitor key usage**:
```bash
# Get comprehensive usage statistics
curl -H "Authorization: Bearer admin-super-key-change-in-production" \
  "http://localhost:8888/api/v1/admin/api-keys/stats/usage"

# Check specific key usage
curl -H "Authorization: Bearer admin-super-key-change-in-production" \
  "http://localhost:8888/api/v1/admin/api-keys/4"

# Search keys by name
curl -H "Authorization: Bearer admin-super-key-change-in-production" \
  "http://localhost:8888/api/v1/admin/api-keys?search=production"
```

### Testing New API Keys

1. **Test API key directly**:
```bash
# Use API key directly (recommended)
curl -H "Authorization: Bearer your-new-api-key" \
  "http://localhost:8888/api/v1/series/83268"
```

2. **Or get JWT token** (alternative):
```bash
curl -X POST "http://localhost:8888/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"api_key": "your-new-api-key"}'

# Use token
TOKEN="your-jwt-token-here"
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8888/api/v1/series/83268"
```

3. **Verify rate limiting**:
```bash
# Make rapid requests to test rate limiting
for i in {1..10}; do
  curl -H "Authorization: Bearer your-new-api-key" \
    "http://localhost:8888/api/v1/series/83268" &
done
```

4. **Check usage tracking**:
```bash
# View updated usage statistics
curl -H "Authorization: Bearer admin-super-key-change-in-production" \
  "http://localhost:8888/api/v1/admin/api-keys/4"
```


### Troubleshooting

**Invalid API key errors**:
- Verify key exists in database via admin endpoints
- Check that `active: true` using admin API
- Ensure key hasn't expired

**Rate limiting issues**:
- Check key's `rate_limit` setting via admin API
- Monitor usage stats via `/admin/api-keys/stats/usage`
- Verify global rate limit settings in environment

**Authentication failures**:
- Ensure proper Bearer token format
- Check JWT expiration (default 7 days)
- Verify SECRET_KEY consistency across services
- Check admin key permissions for management operations

## Deployment

### Production Setup

1. **Generate secure secrets**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

2. **Configure production API keys** (see [API Key Management](#api-key-management) section)

3. **Configure resource limits** in `docker-compose.yml`

4. **Enable monitoring** with Prometheus/Grafana

### GitLab CI/CD

Example `.gitlab-ci.yml`:

```yaml
deploy:
  stage: deploy
  script:
    - docker-compose pull
    - docker-compose up -d
  only:
    - main
```

## Monitoring

### Health Endpoint

```bash
GET /health
```

Returns service status and cache statistics.

### Logs

Structured JSON logging with request tracing:

```bash
docker-compose logs -f api
```

### Metrics

Prometheus metrics available at `/metrics` (if enabled).

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start services
docker-compose up redis db

# Run API locally
uvicorn app.main:app --reload

# Run workers
celery -A app.workers.celery_app worker --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info
```

### Database Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

### Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app
```

## Troubleshooting

### Common Issues

1. **TVDB Authentication Failed**
   - Verify API key in `.env`
   - Check TVDB account status

2. **Cache Not Working**
   - Check Redis connection
   - Verify Redis URL in environment

3. **Database Connection Failed**
   - Check PostgreSQL status
   - Verify DATABASE_URL

4. **Rate Limiting**
   - Check client API key
   - Adjust rate limits in config

### Debug Mode

Enable debug mode for detailed logging:

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

## API Documentation

Interactive API documentation available at:
- Swagger UI: `http://localhost:8888/api/v1/docs`
- ReDoc: `http://localhost:8888/api/v1/redoc`

## Performance

### Benchmarks

- **Cache Hit**: ~50ms response time
- **Cache Miss**: ~200ms response time
- **Throughput**: 1000+ requests/second

### Optimization Tips

1. **Prefetch popular content** using cache warming
2. **Adjust TTL values** based on content update frequency
3. **Scale horizontally** by adding more API instances
4. **Use Redis Cluster** for high availability

## Documentation

- [TVDB Compliance Guide](docs/TVDB_COMPLIANCE.md) - Detailed TVDB v4 API compatibility information
- [API Documentation](http://localhost:8888/api/v1/docs) - Interactive Swagger UI (when running)

## Examples

See the [examples](examples/) directory for:

- `test_tvdb_compliance.py` - Test script to verify TVDB compatibility
- `manage_api_keys.py` - Python example for API key management  
- `create_user_key.sh` - Bash script to create user-supported keys

### Quick Test

```bash
# Run compliance test
python3 examples/test_tvdb_compliance.py

# Create a new user-supported key
./examples/create_user_key.sh
```

## Creating User-Supported Keys

User-supported keys require a PIN (for open-source projects where users have their own TVDB subscription):

```bash
# Get admin token
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8888/login \
  -H "Content-Type: application/json" \
  -d '{"apikey": "admin-super-key-change-in-production"}' | jq -r .data.token)

# Create user-supported key with PIN
curl -X POST http://localhost:8888/api/v1/admin/api-keys \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Community Project",
    "description": "Open-source project requiring user PIN",
    "rate_limit": 50,
    "requires_pin": true,
    "pin": "user-pin-here"
  }'
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- GitHub Issues: [Repository Issues](https://github.com/your-repo/issues)
- Documentation: This README
- TVDB Support: [support.thetvdb.com](https://support.thetvdb.com/)

---

**Note**: This proxy is designed for legitimate use cases that require local caching. Please respect TVDB's terms of service and API usage guidelines.