# Day-to-day Usage

## Deploying an app

### Python / FastAPI / Flask / Django

1. **Applications → New App** → pick the type, give it a port (e.g. `8000`).
2. Add a **startup command** if the default isn't right. Examples:
   - FastAPI: `uvicorn main:app --host 0.0.0.0 --port 8000`
   - Flask:   `gunicorn -w 2 -b 0.0.0.0:5000 wsgi:app`
   - Django:  `gunicorn -w 3 -b 0.0.0.0:8000 myproj.wsgi`
3. **Deploy** → choose Git pull OR upload a ZIP.
4. Open the app row → **Logs** to follow stdout.
5. Hit **Start**.

For Python apps, run `pip install` once via the Terminal or include a build
step in the startup command (`pip install -r requirements.txt && uvicorn …`).

### Node.js

```
startup_command:  npm install && node index.js
port:             3000
```

### PHP

```
startup_command:  (leave blank — defaults to php -S 0.0.0.0:8080)
port:             8080
```

### Static site

Upload via the file manager, set port (default 8080), Start.

### Custom domain

Set the `domain` field, then add a server block to Nginx:

```nginx
server {
    listen 80;
    server_name myapp.example.com;
    location / { proxy_pass http://127.0.0.1:<PORT>; proxy_set_header Host $host; }
}
```

Then `sudo certbot --nginx -d myapp.example.com`.

## Docker

Use **Docker → Run Container** for quick image deploys, or **Compose** to
paste a full `docker-compose.yml`. The compose file is written to
`/var/lib/pdcloud/apps/<name>/docker-compose.yml`.

## File manager

- Click a folder to enter, click a file to edit (text only, ≤2 MB).
- Upload via the **Upload** button.
- ZIPs get an extract button automatically.

## Terminal

A *restricted* single-command runner. Each command runs `bash -lc <cmd>` in
the app workspace, with output captured. Destructive patterns are blocked
and every command is logged.

For a full interactive shell, SSH into the host instead — the browser
terminal is a convenience for quick `git status` / `pip install` etc.

## Backups

- Manual via **Backups → Backup Now**.
- Nightly automatic at 03:00 UTC (configurable in `scheduler.py`).
- Backups are gzipped tarballs at `/var/lib/pdcloud/backups/`.
- Download or delete from the UI.

## Telegram

**Settings → Telegram** → bot token (from @BotFather) + chat ID
(from @userinfobot or @RawDataBot). Send test, then you'll receive:

- ✅/❌ Deployments
- 💥 Crashes (with auto-restart status)
- ⚠️ Resource alerts (CPU / RAM / disk over 90%)
- 💾 Backup completions

## Updating the panel

```bash
cd ~/pd-cloud-personal && git pull
sudo bash deploy/install.sh
```

The installer is idempotent — it won't overwrite your DB or admin account.
