#!/usr/bin/env bash
# Remove the panel (KEEPS your /var/lib/pdcloud data + backups)
set -e
if [[ "$EUID" -ne 0 ]]; then echo "Run as root"; exit 1; fi
systemctl stop pdcloud || true
systemctl disable pdcloud || true
rm -f /etc/systemd/system/pdcloud.service
rm -f /etc/nginx/sites-enabled/pdcloud /etc/nginx/sites-available/pdcloud
nginx -t && systemctl reload nginx || true
rm -rf /opt/pdcloud
echo "Uninstalled. Data preserved at /var/lib/pdcloud."
