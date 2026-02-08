#!/usr/bin/env bash
set -euo pipefail

DOMAIN="prosody-checker.pbconseil.ovh"
REPO_URL="https://github.com/paulsmpl/prosody-yt-scoring.git"
APP_DIR="$HOME/prosody-yt-scoring"
NGINX_AVAILABLE="/etc/nginx/sites-available/${DOMAIN}"
NGINX_ENABLED="/etc/nginx/sites-enabled/${DOMAIN}"
NGINX_HTTP_CONF="deploy/nginx-prosody-checker.http.conf"
NGINX_SSL_CONF="deploy/nginx-prosody-checker.conf"

sudo apt update
sudo apt install -y git nginx certbot python3-certbot-nginx

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
fi

if [ ! -d "$APP_DIR" ]; then
  git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"
git pull

docker compose up -d --build

sudo cp "$NGINX_HTTP_CONF" "$NGINX_AVAILABLE"
if [ ! -L "$NGINX_ENABLED" ]; then
  sudo ln -s "$NGINX_AVAILABLE" "$NGINX_ENABLED"
fi

sudo nginx -t
sudo systemctl restart nginx

if [ ! -d "/etc/letsencrypt/live/${DOMAIN}" ]; then
  sudo certbot --nginx -d "$DOMAIN"
fi

sudo cp "$NGINX_SSL_CONF" "$NGINX_AVAILABLE"
sudo nginx -t
sudo systemctl restart nginx

sudo systemctl restart nginx

echo "Done. Visit https://${DOMAIN}"