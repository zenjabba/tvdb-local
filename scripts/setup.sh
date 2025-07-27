#!/bin/bash

# TVDB Proxy Setup Script
set -e

echo "🚀 Setting up TVDB Proxy..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your TVDB API key before continuing!"
    echo "   Required: TVDB_API_KEY, SECRET_KEY"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Generate secret key if not set
if grep -q "your_super_secret_key_here_change_this_in_production" .env; then
    echo "🔑 Generating secure secret key..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    sed -i.bak "s/your_super_secret_key_here_change_this_in_production/$SECRET_KEY/" .env
    rm .env.bak
fi

# Build and start services
echo "🐳 Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check health
echo "🏥 Checking service health..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ API is healthy!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ API failed to start properly"
        docker-compose logs api
        exit 1
    fi
    sleep 2
done

# Run initial database setup
echo "🗄️  Setting up database..."
docker-compose exec api alembic upgrade head

echo "🎉 Setup complete!"
echo ""
echo "📊 Service URLs:"
echo "   API: http://localhost:8000"
echo "   Health: http://localhost:8000/health"
echo "   Docs: http://localhost:8000/api/v1/docs"
echo ""
echo "🔑 Demo API Keys:"
echo "   demo-key-1 (100 req/min)"
echo "   demo-key-2 (200 req/min)"
echo ""
echo "📖 Quick test:"
echo "   curl -H \"Authorization: Bearer demo-key-1\" http://localhost:8000/api/v1/series/83268"