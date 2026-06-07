# Installation — PD Cloud Personal

Tested on **Ubuntu 24.04 LTS** (works on 22.04 too). Requires sudo / root.

## TL;DR

```bash
git clone https://github.com/yourname/pd-cloud-personal.git
cd pd-cloud-personal
sudo bash deploy/install.sh
```

You'll be asked for an admin username + password during install.

## What the installer does

1. **System packages** — Python 3, Node.js 20, PHP, Nginx, SQLite, PostgreSQL client, Docker engine, ufw.
2. **System user** `pdcloud` (no login, but in `docker` group).
3. **Directories**
   - `/opt/pdcloud/` — source + venv
   - `/var/lib/pdcloud/` — DB, apps, backups
   - `/var/log/pdcloud/` — app logs
   - `/etc/pdcloud/pdcloud.env` — config (mode 640)
4. **Python venv** with all backend deps.
5. **Initial admin** account in the SQLite DB.
6. **systemd service** `pdcloud.service` — runs FastAPI under uvicorn, restarts on failure.
7. **Nginx** reverse proxy on :80, login rate-limit, gzip, security headers.
8. **logrotate** rule for `/var/log/pdcloud/*.log`.
9. **ufw** allows 22, 80, 443.

## Verifying

```bash
systemctl status pdcloud
journalctl -u pdcloud -f
curl http://127.0.0.1/api/health
```

Open `http://<server-ip>/` in your browser and sign in.

## Updating

```bash
cd pd-cloud-personal && git pull
sudo bash deploy/install.sh    # idempotent; reuses venv and admin account
sudo systemctl restart pdcloud
```

## Uninstall

```bash
sudo bash deploy/uninstall.sh   # keeps data
sudo rm -rf /var/lib/pdcloud /etc/pdcloud /var/log/pdcloud   # full purge
```

## Running with Docker (alternative)

```bash
docker compose -f deploy/docker-compose.yml up -d --build
docker compose exec pdcloud python -m app.cli create-admin admin 'strongpassword'
```

Open `http://<server-ip>:8000/`.
