#!/usr/bin/env bash
# =====================================================================
#  PD Cloud Personal — installer for Ubuntu 24.04 (AWS EC2 friendly)
# =====================================================================
#  Usage:    sudo bash deploy/install.sh
#  Idempotent: safe to re-run for updates.
# =====================================================================
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root (use sudo)."; exit 1
fi

# ---------- Configurable ----------
APP_USER="${APP_USER:-pdcloud}"
APP_DIR="${APP_DIR:-/opt/pdcloud}"
DATA_DIR="${DATA_DIR:-/var/lib/pdcloud}"
LOG_DIR="${LOG_DIR:-/var/log/pdcloud}"
ETC_DIR="${ETC_DIR:-/etc/pdcloud}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PORT="${PORT:-8000}"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() { echo -e "\033[1;32m==>\033[0m $*"; }
warn() { echo -e "\033[1;33m[!]\033[0m $*"; }
err() { echo -e "\033[1;31m[x]\033[0m $*"; exit 1; }

# ---------- 1. System packages ----------
log "Installing system packages …"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
  python3 python3-venv python3-pip python3-dev build-essential \
  git curl ca-certificates gnupg unzip tar \
  nginx \
  sqlite3 \
  postgresql-client \
  ufw

# Node.js LTS (for Node app type)
if ! command -v node >/dev/null 2>&1; then
  log "Installing Node.js 20.x …"
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi

# PHP (for PHP app type)
if ! command -v php >/dev/null 2>&1; then
  log "Installing PHP …"
  apt-get install -y php-cli php-fpm php-curl php-mbstring php-xml php-zip
fi

# Docker
if ! command -v docker >/dev/null 2>&1; then
  log "Installing Docker engine …"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
fi

# ---------- 2. System user ----------
if ! id "$APP_USER" >/dev/null 2>&1; then
  log "Creating system user '$APP_USER' …"
  useradd --system --create-home --shell /bin/bash "$APP_USER"
fi
usermod -aG docker "$APP_USER" || true

# ---------- 3. Directories ----------
log "Creating directories …"
mkdir -p "$APP_DIR" "$DATA_DIR" "$DATA_DIR/apps" "$DATA_DIR/backups" "$LOG_DIR" "$ETC_DIR"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR" "$DATA_DIR" "$LOG_DIR"
chown root:"$APP_USER" "$ETC_DIR"; chmod 750 "$ETC_DIR"

# ---------- 4. Code ----------
log "Copying application source to $APP_DIR …"
rsync -a --delete --exclude='__pycache__' --exclude='.git' \
  "$SRC_DIR/backend/" "$APP_DIR/backend/"
rsync -a --delete "$SRC_DIR/frontend/" "$APP_DIR/frontend/"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

# ---------- 5. Python venv ----------
log "Setting up Python virtualenv …"
sudo -u "$APP_USER" $PYTHON_BIN -m venv "$APP_DIR/venv"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip wheel
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt"

# ---------- 6. Environment file ----------
if [[ ! -f "$ETC_DIR/pdcloud.env" ]]; then
  log "Generating $ETC_DIR/pdcloud.env …"
  SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
  cat > "$ETC_DIR/pdcloud.env" <<EOF
# PD Cloud Personal — runtime configuration
PDCLOUD_SECRET_KEY=$SECRET
PDCLOUD_ENV=production
PDCLOUD_HOST=127.0.0.1
PDCLOUD_PORT=$PORT
PDCLOUD_DEBUG=false
PDCLOUD_COOKIE_SECURE=false
# Set to true once you have HTTPS via certbot
PDCLOUD_DATA_DIR=$DATA_DIR
PDCLOUD_APPS_DIR=$DATA_DIR/apps
PDCLOUD_BACKUPS_DIR=$DATA_DIR/backups
PDCLOUD_LOGS_DIR=$LOG_DIR
PDCLOUD_DB_PATH=$DATA_DIR/pdcloud.db
# Telegram (optional — also configurable in UI)
PDCLOUD_TELEGRAM_BOT_TOKEN=
PDCLOUD_TELEGRAM_CHAT_ID=
EOF
  chown root:"$APP_USER" "$ETC_DIR/pdcloud.env"
  chmod 640 "$ETC_DIR/pdcloud.env"
fi

# ---------- 7. Admin account ----------
if [[ ! -f "$DATA_DIR/.admin_initialized" ]]; then
  log "Creating initial admin account …"
  read -rp "Admin username: " ADMIN_USER
  while true; do
    read -rsp "Admin password (>=10 chars): " ADMIN_PASS; echo
    read -rsp "Confirm:                      " ADMIN_PASS2; echo
    [[ "$ADMIN_PASS" == "$ADMIN_PASS2" ]] && [[ ${#ADMIN_PASS} -ge 10 ]] && break
    warn "Mismatch or too short, try again."
  done
  sudo -u "$APP_USER" bash -c "cd $APP_DIR/backend && PDCLOUD_ENV_FILE=$ETC_DIR/pdcloud.env $APP_DIR/venv/bin/python -m app.cli create-admin '$ADMIN_USER' '$ADMIN_PASS'"
  touch "$DATA_DIR/.admin_initialized"
  chown "$APP_USER":"$APP_USER" "$DATA_DIR/.admin_initialized"
fi

# ---------- 8. systemd service ----------
log "Installing systemd unit …"
cp "$SRC_DIR/deploy/pdcloud.service" /etc/systemd/system/pdcloud.service
sed -i "s|@APP_DIR@|$APP_DIR|g; s|@APP_USER@|$APP_USER|g; s|@ETC_DIR@|$ETC_DIR|g; s|@PORT@|$PORT|g" /etc/systemd/system/pdcloud.service
systemctl daemon-reload
systemctl enable pdcloud.service
systemctl restart pdcloud.service

# ---------- 9. Nginx ----------
log "Installing Nginx reverse proxy …"
cp "$SRC_DIR/deploy/nginx.conf" /etc/nginx/sites-available/pdcloud
sed -i "s|@PORT@|$PORT|g" /etc/nginx/sites-available/pdcloud
ln -sf /etc/nginx/sites-available/pdcloud /etc/nginx/sites-enabled/pdcloud
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

# ---------- 10. Log rotation ----------
log "Installing logrotate config …"
cat > /etc/logrotate.d/pdcloud <<EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 640 $APP_USER $APP_USER
    sharedscripts
}
EOF

# ---------- 11. Firewall ----------
if command -v ufw >/dev/null 2>&1; then
  log "Configuring ufw firewall (allow 22, 80, 443) …"
  ufw --force enable || true
  ufw allow 22/tcp || true
  ufw allow 80/tcp || true
  ufw allow 443/tcp || true
fi

log "✅ PD Cloud Personal installed!"
echo
echo "   Panel:  http://$(curl -s -m 2 http://169.254.169.254/latest/meta-data/public-ipv4 || echo "<your-server-ip>")/"
echo "   Logs:   journalctl -u pdcloud -f"
echo "   Config: $ETC_DIR/pdcloud.env"
echo
echo "   For HTTPS:  sudo apt install certbot python3-certbot-nginx && sudo certbot --nginx"
echo "   Then set PDCLOUD_COOKIE_SECURE=true in $ETC_DIR/pdcloud.env and restart: sudo systemctl restart pdcloud"
