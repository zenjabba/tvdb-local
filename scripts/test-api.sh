#!/bin/bash

# TVDB Proxy API Test Script
set -e

BASE_URL="http://localhost:8000"
API_KEY="demo-key-1"

echo "🧪 Testing TVDB Proxy API..."

# Test health endpoint
echo "📊 Testing health endpoint..."
curl -s "$BASE_URL/health" | jq '.'

echo -e "\n🔑 Getting JWT token..."
TOKEN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d "{\"api_key\": \"$API_KEY\"}")

TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" = "null" ]; then
    echo "❌ Failed to get token"
    echo $TOKEN_RESPONSE | jq '.'
    exit 1
fi

echo "✅ Got token: ${TOKEN:0:20}..."

# Test series endpoint
echo -e "\n📺 Testing series endpoint..."
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/series/83268" | jq '.data.name // .error'

# Test series episodes
echo -e "\n📋 Testing series episodes..."
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/series/83268/episodes?page=0" | jq '.meta'

# Test search
echo -e "\n🔍 Testing search..."
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/search/series?q=breaking" | jq '.meta'

# Test movie endpoint  
echo -e "\n🎬 Testing movie endpoint..."
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/movies/1" | jq '.data.name // .error'

# Test people endpoint
echo -e "\n👤 Testing people endpoint..."
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/people/1" | jq '.data.name // .error'

echo -e "\n✅ API tests completed!"