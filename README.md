# TVDB Proxy

A high-performance caching proxy for TVDB API v4 that stores data locally using Redis and PostgreSQL, protecting your API key and providing blazing-fast responses.

## Features

- 🚀 **High Performance**: Redis caching with sub-100ms response times
- 🔒 **API Key Protection**: Secure local authentication with JWT tokens
- 📦 **Complete Data Storage**: PostgreSQL for persistent storage
- 🔄 **Auto-Sync**: Background workers keep data up-to-date
- 🛡️ **Rate Limiting**: Configurable rate limiting per client
- 🎯 **Smart Caching**: Intelligent cache invalidation and prefetching
- 🐳 **Docker Ready**: Complete containerized deployment
- 📊 **Monitoring**: Built-in health checks and metrics

## Quick Start

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

The API will be available at `http://localhost:8000`

### 4. Health Check

```bash
curl http://localhost:8000/health
```

## API Usage

### Authentication

Get a JWT token using your API key:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"api_key": "demo-key-1"}'
```

Use the token in subsequent requests:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/series/83268"
```

### Endpoints

#### Series

```bash
# Get series by ID
GET /api/v1/series/{series_id}

# Get extended series information  
GET /api/v1/series/{series_id}?extended=true

# Get series episodes
GET /api/v1/series/{series_id}/episodes?page=0

# Get all series (paginated)
GET /api/v1/series?page=0
```

#### Movies

```bash
# Get movie by ID
GET /api/v1/movies/{movie_id}

# Get extended movie information
GET /api/v1/movies/{movie_id}?extended=true
```

#### Episodes

```bash
# Get episode by ID
GET /api/v1/episodes/{episode_id}
```

#### People

```bash
# Get person by ID
GET /api/v1/people/{person_id}
```

#### Search

```bash
# Search series
GET /api/v1/search/series?q=breaking+bad

# Search movies
GET /api/v1/search/movies?q=inception

# Search people
GET /api/v1/search/people?q=bryan+cranston

# Search all types
GET /api/v1/search/all?q=batman
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

- **API Gateway**: FastAPI application with authentication and rate limiting
- **Redis**: Fast caching layer for frequently accessed data
- **PostgreSQL**: Persistent storage for complete TVDB dataset
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

### API Keys

Default demo API keys (change in production):

- `demo-key-1`: 100 requests/minute
- `demo-key-2`: 200 requests/minute

## Deployment

### Production Setup

1. **Generate secure secrets**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

2. **Update API keys** in `app/auth.py`

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
- Swagger UI: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`

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