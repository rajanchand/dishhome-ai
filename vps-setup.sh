#!/bin/bash
set -e

echo "Setting up DishHome AI on VPS..."

cd /root/dishhome-ai

# Make sure we have latest code
git pull origin main || echo "Git pull failed, proceeding anyway"

# Prepare .env
cp .env.example .env
if ! grep -q "FRONTEND_PORT=3000" .env; then
    echo "FRONTEND_PORT=3000" >> .env
fi
if ! grep -q "APP_PORT=8000" .env; then
    echo "APP_PORT=8000" >> .env
fi

# Run docker compose
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build

# Configure Nginx
cat << 'EOF' > /etc/nginx/sites-available/dishhome.conf
server {
    listen 80;
    server_name ai.zero-trust-security.org dishhome.zero-trust-security.org; # Replace with new domain if needed

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

# Enable site and restart nginx
ln -sf /etc/nginx/sites-available/dishhome.conf /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

echo "Setup completed successfully!"
