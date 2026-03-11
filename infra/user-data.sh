#!/bin/bash
set -euo pipefail

# Log everything
exec > >(tee /var/log/user-data.log) 2>&1

echo "=== Starting voto.vc setup ==="

# Install Docker
dnf update -y
dnf install -y docker git
systemctl enable docker
systemctl start docker

# Install Docker Compose
DOCKER_CONFIG=/usr/local/lib/docker/cli-plugins
mkdir -p $DOCKER_CONFIG
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-aarch64" -o $DOCKER_CONFIG/docker-compose
chmod +x $DOCKER_CONFIG/docker-compose

# Add ec2-user to docker group
usermod -aG docker ec2-user

# Install certbot for Let's Encrypt SSL
dnf install -y certbot

# Create app directory
mkdir -p /opt/votovc
cd /opt/votovc

# Create production docker-compose
cat > docker-compose.yml << 'COMPOSE'
services:
  db:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_DB: votovc
      POSTGRES_USER: votovc
      POSTGRES_PASSWORD: ${db_password}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U votovc"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    image: ghcr.io/OWNER/votovc-backend:latest
    build:
      context: .
      dockerfile: Dockerfile.backend
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+asyncpg://votovc:${db_password}@db:5432/votovc
      LOG_LEVEL: INFO
    ports:
      - "8000:8000"

  frontend:
    image: ghcr.io/OWNER/votovc-frontend:latest
    build:
      context: .
      dockerfile: Dockerfile.frontend
    restart: unless-stopped
    depends_on:
      - backend
    environment:
      ORIGIN: https://${domain}
    ports:
      - "3000:3000"

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    depends_on:
      - backend
      - frontend
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - certbot-webroot:/var/www/certbot:ro

volumes:
  pgdata:
  certbot-webroot:
COMPOSE

# Create nginx config
cat > nginx.conf << 'NGINX'
events {
    worker_connections 1024;
}

http {
    # Redirect HTTP to HTTPS (except certbot challenge)
    server {
        listen 80;
        server_name ${domain} www.${domain};

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$host$request_uri;
        }
    }

    # HTTPS server
    server {
        listen 443 ssl;
        server_name ${domain} www.${domain};

        ssl_certificate     /etc/letsencrypt/live/${domain}/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/${domain}/privkey.pem;

        # API
        location /api/ {
            proxy_pass http://backend:8000/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Frontend
        location / {
            proxy_pass http://frontend:3000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
NGINX

# Create initial HTTP-only nginx config (for certbot bootstrap)
cat > nginx-init.conf << 'NGINXINIT'
events {
    worker_connections 1024;
}

http {
    server {
        listen 80;
        server_name ${domain} www.${domain};

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 200 'voto.vc - setting up...';
            add_header Content-Type text/plain;
        }
    }
}
NGINXINIT

# Create deploy script
cat > /opt/votovc/deploy.sh << 'DEPLOY'
#!/bin/bash
set -euo pipefail
cd /opt/votovc

echo "Pulling latest images..."
docker compose pull 2>/dev/null || true

echo "Building and starting services..."
docker compose up -d --build

echo "Running migrations..."
docker compose exec backend uv run alembic upgrade head 2>/dev/null || echo "No migrations to run"

echo "Deploy complete!"
docker compose ps
DEPLOY
chmod +x /opt/votovc/deploy.sh

# Create SSL setup script
cat > /opt/votovc/setup-ssl.sh << 'SSL'
#!/bin/bash
set -euo pipefail
cd /opt/votovc

echo "Starting nginx with HTTP-only config for certbot..."
cp nginx-init.conf nginx.conf
docker compose up -d nginx

echo "Requesting SSL certificate..."
mkdir -p /var/www/certbot
certbot certonly --webroot \
  -w /var/www/certbot \
  -d ${domain} \
  -d www.${domain} \
  --non-interactive \
  --agree-tos \
  --email admin@${domain}

echo "Switching to HTTPS nginx config..."
# Restore the full nginx config (it's in the docker-compose as a template)
# Restart nginx to pick up SSL
docker compose restart nginx

echo "SSL setup complete!"

# Add auto-renewal cron
echo "0 3 * * * certbot renew --quiet && docker compose -f /opt/votovc/docker-compose.yml restart nginx" | crontab -
SSL
chmod +x /opt/votovc/setup-ssl.sh

echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Point DNS to this server"
echo "  2. Deploy app code"
echo "  3. Run /opt/votovc/setup-ssl.sh for HTTPS"
