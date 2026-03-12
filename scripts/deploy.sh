#!/usr/bin/env bash
set -euo pipefail

SERVER="ec2-user@44.216.159.100"
SSH_KEY="$HOME/.ssh/votovc_deploy"
REMOTE_APP="/opt/votovc/app"
REMOTE_ROOT="/opt/votovc"

ssh_cmd="ssh -i $SSH_KEY -o ConnectTimeout=10"

echo "==> Syncing code to server..."
rsync -avz --delete \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='.terraform' \
  --exclude='*.tfstate*' \
  --exclude='terraform.tfvars' \
  -e "$ssh_cmd" \
  "$(git rev-parse --show-toplevel)/" "$SERVER:$REMOTE_APP/"

echo "==> Building and deploying..."
$ssh_cmd "$SERVER" << 'EOF'
  cd /opt/votovc/app

  # Build production images
  docker build -f Dockerfile.backend.prod -t votovc-backend:latest .
  docker build -f Dockerfile.frontend.prod -t votovc-frontend:latest .

  cd /opt/votovc

  # Restart app containers (keep db running)
  docker compose stop backend frontend nginx 2>/dev/null || true
  docker compose rm -f backend frontend nginx 2>/dev/null || true
  docker compose up -d

  echo ""
  echo "==> Deploy complete!"
  docker compose ps
EOF
