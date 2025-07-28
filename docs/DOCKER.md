# TVDB Local Proxy - Docker Images

Docker images for the TVDB Local Proxy are available on Docker Hub.

## Available Images

- `zenjabba/tvdb-local:latest` - Main API server
- `zenjabba/tvdb-local-worker:latest` - Celery worker for background tasks

## Quick Start

### Using Docker Compose (Recommended)

1. Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  api:
    image: zenjabba/tvdb-local:latest
    ports:
      - "8888:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/tvdb_proxy
      - REDIS_URL=redis://redis:6379/0
      - TVDB_API_KEY=${TVDB_API_KEY}
      - TVDB_PIN=${TVDB_PIN}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - db
      - redis
    restart: unless-stopped

  worker:
    image: zenjabba/tvdb-local-worker:latest
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/tvdb_proxy
      - REDIS_URL=redis://redis:6379/0
      - TVDB_API_KEY=${TVDB_API_KEY}
      - TVDB_PIN=${TVDB_PIN}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: tvdb_proxy
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

2. Create `.env` file:
```env
TVDB_API_KEY=your-tvdb-api-key
TVDB_PIN=your-tvdb-pin  # Optional
SECRET_KEY=your-secret-key
```

3. Start the services:
```bash
docker-compose up -d
```

### Using Docker Run

For a minimal setup (requires external PostgreSQL and Redis):

```bash
docker run -d \
  --name tvdb-proxy \
  -p 8888:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/dbname \
  -e REDIS_URL=redis://host:6379/0 \
  -e TVDB_API_KEY=your-api-key \
  -e SECRET_KEY=your-secret-key \
  zenjabba/tvdb-local:latest
```

## Tags

- `latest` - Latest stable release from main branch
- `main` - Latest build from main branch
- `v1.0.0`, `v1.0`, `v1` - Semantic versioning tags
- `main-abc1234` - Specific commit builds

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TVDB_API_KEY` | Your TVDB API key | Yes |
| `TVDB_PIN` | Your TVDB PIN (if required) | No |
| `SECRET_KEY` | JWT signing secret | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `DEBUG` | Enable debug mode | No |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | Default rate limit | No |

## Multi-Architecture Support

Images are built for both `linux/amd64` and `linux/arm64` architectures.

## Source Code

The source code is available at: https://github.com/zenjabba/tvdb-local