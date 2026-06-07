# Security Hardening Guide

PD Cloud Personal ships with sensible defaults — this doc lists everything
already in place plus extra steps you should take in production.

## Built-in protections

| Area | Implementation |
|---|---|
| **Auth** | Single admin · bcrypt(12) password hashing · JWT in HttpOnly cookies (12h) |
| **Login** | 5 wrong attempts → 15 min account lockout · 10 req/min rate-limit at Nginx **and** SlowAPI |
| **CSRF** | Double-submit cookie + `X-CSRF-Token` header validated on every state-changing call |
| **XSS** | Strict CSP, `X-Content-Type-Options: nosniff`, all user content escaped client-side |
| **Cookies** | `HttpOnly`, `Secure` (when HTTPS), `SameSite=Lax` |
| **Headers** | CSP, HSTS, X-Frame-Options=SAMEORIGIN, Referrer-Policy, Permissions-Policy |
| **File access** | All file operations clamped to `/var/lib/pdcloud/apps` — path traversal blocked |
| **Terminal** | Restricted command runner · blocklist (`rm -rf /`, `mkfs`, fork bombs…) · audit-logged · 30s timeout |
| **Uploads** | Extension blocklist · path normalization · safe zip extraction (Zip-Slip prevented) |
| **DB queries** | SQLite paths restricted to managed dirs; PG queries logged |
| **Audit** | Every login, password change, app/file/docker/terminal/db action logged with IP |
| **systemd** | `NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`, `PrivateTmp`, kernel/cgroup protections, `RestrictSUIDSGID` |

## Recommended additional hardening

### 1. Use HTTPS only

```bash
sudo certbot --nginx -d panel.example.com --redirect
sudo sed -i 's/PDCLOUD_COOKIE_SECURE=false/PDCLOUD_COOKIE_SECURE=true/' /etc/pdcloud/pdcloud.env
sudo systemctl restart pdcloud
```

### 2. SSH hardening

```bash
# /etc/ssh/sshd_config
PermitRootLogin no
PasswordAuthentication no
AllowUsers ubuntu
```

```bash
sudo systemctl restart ssh
```

### 3. Restrict panel by IP

In the AWS Security Group, limit HTTPS 443 to your office/home CIDR if you don't
need world access. Alternatively put it behind a VPN (Tailscale / WireGuard).

### 4. Fail2ban for the panel

```bash
sudo apt install -y fail2ban
sudo tee /etc/fail2ban/jail.d/pdcloud.conf <<'EOF'
[pdcloud-login]
enabled = true
port    = http,https
logpath = /var/log/nginx/access.log
maxretry = 10
findtime = 600
bantime  = 3600
filter   = pdcloud-login
EOF

sudo tee /etc/fail2ban/filter.d/pdcloud-login.conf <<'EOF'
[Definition]
failregex = ^<HOST> .* "POST /api/auth/login HTTP.*" 401
ignoreregex =
EOF

sudo systemctl restart fail2ban
```

### 5. Rotate the secret

```bash
sudo sed -i "s/PDCLOUD_SECRET_KEY=.*/PDCLOUD_SECRET_KEY=$(python3 -c 'import secrets;print(secrets.token_urlsafe(64))')/" /etc/pdcloud/pdcloud.env
sudo systemctl restart pdcloud
```

(Will log everyone out — fine for a single-admin panel.)

### 6. Off-host, encrypted backups

Sync `/var/lib/pdcloud/backups` to S3 with default server-side encryption,
or use [`restic`](https://restic.net/) with a passphrase.

### 7. Keep the host patched

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 8. Monitor

- `journalctl -u pdcloud -f` for backend logs
- `/var/log/nginx/access.log` for HTTP
- Activity page in the panel for human-readable audit
- Telegram alerts for crashes & resource spikes

## Threat model boundaries

PD Cloud Personal is designed for **one trusted administrator**. It is **not**
multi-tenant. The browser terminal can run any command the `pdcloud` user can
(scoped to the apps dir & blocklist). If an attacker steals an admin session
cookie they will have those same privileges. Always:

- use a strong password
- enable HTTPS
- restrict source IPs when possible
- rotate the JWT secret if you suspect compromise
