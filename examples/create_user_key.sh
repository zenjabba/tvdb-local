#\!/bin/bash

# First, get an admin token
echo "Getting admin token..."
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8888/login \
  -H "Content-Type: application/json" \
  -d '{"apikey": "admin-super-key-change-in-production"}'  < /dev/null |  jq -r .data.token)

echo "Admin token obtained\!"

# Create a new user-supported key with PIN
echo -e "\nCreating user-supported API key..."
curl -X POST http://localhost:8888/api/v1/admin/api-keys \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My User App",
    "description": "User-supported key for community app",
    "rate_limit": 50,
    "requires_pin": true,
    "pin": "5678"
  }' | jq

echo -e "\nDone\! The new key requires PIN: 5678"
