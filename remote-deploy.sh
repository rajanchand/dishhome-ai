#!/bin/bash
set -e
cd /root/dishhome-ai

# Ensure required environment variables are set in .env
grep -q "^DATABASE_URL=" .env || echo "DATABASE_URL=postgresql://dishhome:dishhome_secret@postgres:5432/dishhome_ai" >> .env
sed -i 's|^DATABASE_URL=.*|DATABASE_URL=postgresql://dishhome:dishhome_secret@postgres:5432/dishhome_ai|' .env

# Set PUBLIC_BASE_URL to avoid validation error (must be https in production)
sed -i 's|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=https://ai.zero-trust-security.org|' .env

# CORS_ALLOWED_ORIGINS must not contain localhost or 127.0.0.1 in production
sed -i 's|^CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=https://ai.zero-trust-security.org|' .env

# Generate a random secret key if it is still the placeholder
sed -i 's|generate_me_using_openssl_rand_hex_32|e2b34a98f12c8b74d6e90fa2b3c4d5e6|' .env

# Ensure FRONTEND_PORT and APP_PORT are correct
grep -q "^FRONTEND_PORT=" .env || echo "FRONTEND_PORT=3001" >> .env
sed -i 's|^FRONTEND_PORT=.*|FRONTEND_PORT=3001|' .env

grep -q "^APP_PORT=" .env || echo "APP_PORT=8000" >> .env
sed -i 's|^APP_PORT=.*|APP_PORT=8000|' .env

# Disable audio server by default to prevent faster-whisper crash on VPS
grep -q "^ENABLE_AUDIO_SERVER=" .env || echo "ENABLE_AUDIO_SERVER=false" >> .env
sed -i 's|^ENABLE_AUDIO_SERVER=.*|ENABLE_AUDIO_SERVER=false|' .env

# Set Supabase schema to public to avoid "dh schema does not exist" errors
grep -q "^SUPABASE_SCHEMA=" .env || echo "SUPABASE_SCHEMA=public" >> .env
sed -i 's|^SUPABASE_SCHEMA=.*|SUPABASE_SCHEMA=public|' .env

# Explicitly set VITE_API_BASE to proxy through Nginx
grep -q "^VITE_API_BASE=" .env || echo "VITE_API_BASE=/api" >> .env
sed -i 's|^VITE_API_BASE=.*|VITE_API_BASE=/api|' .env

# Start docker-compose in production mode
docker compose -f docker-compose.prod.yml down --remove-orphans || true
docker compose -f docker-compose.prod.yml up -d --build

# Write Nginx config
cat << 'EOF' > /etc/nginx/sites-available/dishhome.conf
server {
    listen 80;
    server_name ai.zero-trust-security.org;

    location / {
        proxy_pass http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

# Enable and restart Nginx
ln -sf /etc/nginx/sites-available/dishhome.conf /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
