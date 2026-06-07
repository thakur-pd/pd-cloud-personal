# PD Cloud Personal

A modern self-hosted personal cloud hosting control panel for a single administrator. Built for AWS EC2 Ubuntu 24.04, but runs on any modern Linux host.

PD Cloud Personal is a lightweight blend of Pterodactyl + Coolify + Easypanel + AponCloud — designed for **one person, one server, total control**.

## ✨ Features

- 🔐 **Single-admin auth** — JWT sessions, bcrypt passwords, rate-limited login, lockout, audit log
- 🎨 **Premium UI** — Bootstrap 5, White + Neon Mint theme, dark mode, mobile-responsive
- 📊 **Live dashboard** — CPU, RAM, Disk, Network, Load, Uptime, Services
- 🚀 **App hosting** — Python / Flask / Django / FastAPI / Node.js / PHP / Static
- 📦 **Deployment** — ZIP upload, GitHub clone, Git pull, env vars, custom domains, port mapping
- 🐳 **Docker manager** — Containers, logs, compose support
- 📁 **File manager** — Browse, upload, edit, rename, extract zip
- 💻 **Browser terminal** — Restricted shell with full audit logging
- 🗄️ **DB manager** — SQLite browser, PostgreSQL integration, query runner, backup/restore
- 📈 **Real-time monitoring** — Live graphs (Chart.js) with WebSocket-style polling
- 🔔 **Telegram notifications** — Deploys, crashes, resource alerts, backups
- 💾 **Backups** — Manual + scheduled, snapshots, download/restore
- 🛡️ **Security** — CSRF, XSS, CSP, secure cookies, rate limits, file validation, headers
- ☁️ **AWS-ready** — Nginx reverse proxy, systemd services, log rotation, autostart

## 🚀 Quick install (Ubuntu 24.04 / EC2)

```bash
curl -fsSL https://raw.githubusercontent.com/yourname/pd-cloud-personal/main/deploy/install.sh -o install.sh
sudo bash install.sh
```

Or locally from a clone:

```bash
sudo bash deploy/install.sh
```

The installer will:

1. Install system deps (Python 3.12, Node.js, Docker, Nginx, PostgreSQL client)
2. Create the `pdcloud` system user
3. Set up a Python venv and install requirements
4. Initialize the SQLite DB and create the admin account (you'll be prompted)
5. Install the systemd unit (`pdcloud.service`) and start it
6. Configure Nginx as a reverse proxy on port 80/443

Default panel URL: `http://<server-ip>/`

## 📚 Docs

- [`docs/INSTALL.md`](docs/INSTALL.md) — Full installation
- [`docs/AWS_DEPLOY.md`](docs/AWS_DEPLOY.md) — EC2 deployment walkthrough
- [`docs/SECURITY.md`](docs/SECURITY.md) — Hardening guide
- [`docs/API.md`](docs/API.md) — REST API reference
- [`docs/USAGE.md`](docs/USAGE.md) — Day-to-day operations

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Browser (Bootstrap 5 + Chart.js + Vanilla JS SPA)      │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTPS
┌───────────────────────▼─────────────────────────────────┐
│  Nginx (reverse proxy, TLS, static, rate-limit)         │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│  FastAPI (async, JWT, REST)                             │
│  ├── auth   ├── apps    ├── docker  ├── files           │
│  ├── term   ├── db      ├── system  ├── backups         │
│  └── notify (Telegram)                                  │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│  SQLite (panel state) + systemd (app processes)         │
│  Docker engine, host filesystem, PostgreSQL (optional)  │
└─────────────────────────────────────────────────────────┘
```

## License

MIT — personal use.
