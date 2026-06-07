# AWS EC2 Deployment Guide

A step-by-step walkthrough for putting PD Cloud Personal on a fresh
Ubuntu 24.04 EC2 instance.

## 1. Launch the instance

| Setting | Recommendation |
|---|---|
| AMI | **Ubuntu Server 24.04 LTS (HVM), SSD Volume Type** |
| Instance | `t3.small` (2 vCPU / 2 GB) minimum · `t3.medium` for comfort |
| Storage | 30 GB gp3 (more if you'll host apps) |
| Key pair | Create / select your SSH key |
| Security group | Inbound: SSH 22 (your IP), HTTP 80 (anywhere), HTTPS 443 (anywhere) |

> **Elastic IP**: allocate and associate one so your panel URL stays stable.

## 2. SSH in

```bash
ssh -i your-key.pem ubuntu@<public-ip>
```

## 3. Get the code

```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/yourname/pd-cloud-personal.git
cd pd-cloud-personal
```

## 4. Install

```bash
sudo bash deploy/install.sh
```

When prompted, choose a strong username + password (≥10 chars).

## 5. Point a domain (optional but recommended)

In Route 53 (or your DNS provider) create an **A record**:
`panel.example.com  →  <elastic-ip>`.

Edit `/etc/nginx/sites-available/pdcloud` and change
`server_name _;` to `server_name panel.example.com;`. Reload:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## 6. Enable HTTPS

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d panel.example.com --agree-tos -m you@example.com --redirect
```

Then turn on secure cookies:

```bash
sudo sed -i 's/PDCLOUD_COOKIE_SECURE=false/PDCLOUD_COOKIE_SECURE=true/' /etc/pdcloud/pdcloud.env
sudo systemctl restart pdcloud
```

Certbot auto-renew is already wired by the snap/apt package.

## 7. Lock down the security group

After confirming HTTPS works, **remove HTTP 80** from your SG if you don't need it
(certbot's auto-renew uses HTTP-01 challenge — leave 80 open if you rely on it,
otherwise switch to DNS-01).

## 8. Backups off-host

By default backups are stored under `/var/lib/pdcloud/backups`.
A common pattern is to sync nightly to S3:

```bash
sudo apt install -y awscli
aws configure   # provide IAM keys with s3:PutObject for your bucket
sudo crontab -e
# Add:
30 3 * * * aws s3 sync /var/lib/pdcloud/backups s3://my-bucket/pdcloud-backups/ --delete
```

For zero-secret access on EC2, attach an **IAM Role** to the instance with an
S3 write policy instead of using static keys.

## 9. Telemetry / alerts

Open the panel → **Settings → Telegram** → paste your bot token and chat ID.
You'll now get DMs for deployments, crashes, resource alerts, and backups.

## 10. Maintenance

```bash
# Logs
journalctl -u pdcloud -f
tail -f /var/log/pdcloud/*.log

# Restart
sudo systemctl restart pdcloud nginx

# Update
cd ~/pd-cloud-personal && git pull
sudo bash deploy/install.sh
```

## Common AWS gotchas

- **502 Bad Gateway** — check `journalctl -u pdcloud -n 100`, the FastAPI process likely failed to bind.
- **Login cookie not being set** — you're on HTTP but `PDCLOUD_COOKIE_SECURE=true`. Either run via HTTPS or set it to `false`.
- **Permission denied talking to Docker** — the `pdcloud` user must be in the `docker` group (installer handles this, but if you ran updates as another user reapply: `sudo usermod -aG docker pdcloud && sudo systemctl restart pdcloud`).
- **Disk full from logs** — logrotate is configured but if you raise traffic, tighten retention in `/etc/logrotate.d/pdcloud`.
