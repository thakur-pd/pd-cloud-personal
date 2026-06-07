# REST API Reference

All endpoints are JSON. Authenticated endpoints require either:

- the `pdcloud_session` HttpOnly cookie (set automatically after login), **OR**
- an `Authorization: Bearer <token>` header

State-changing requests (`POST`, `PATCH`, `DELETE`) additionally require the
`X-CSRF-Token` header to match the `csrf_token` cookie (set on login).

## Auth

| Method | Path | Body | Description |
|---|---|---|---|
| POST | `/api/auth/login`           | `{username, password}`             | Returns JWT + sets cookies |
| POST | `/api/auth/logout`          | —                                   | Clears cookies |
| GET  | `/api/auth/me`              | —                                   | Current admin |
| POST | `/api/auth/change-password` | `{current_password, new_password}`  | Update password |

## System

| Method | Path | Description |
|---|---|---|
| GET | `/api/health`            | Public health probe |
| GET | `/api/system/snapshot`   | CPU/RAM/Disk/Net/Load/Uptime |
| GET | `/api/system/services`   | Top processes |
| GET | `/api/system/dashboard`  | Composite payload for the dashboard view |

## Applications

| Method | Path | Description |
|---|---|---|
| GET    | `/api/apps`                       | List |
| POST   | `/api/apps`                       | Create |
| GET    | `/api/apps/{id}`                  | Detail |
| PATCH  | `/api/apps/{id}`                  | Update |
| DELETE | `/api/apps/{id}`                  | Delete app + files |
| POST   | `/api/apps/{id}/start`            | Start process |
| POST   | `/api/apps/{id}/stop`             | Stop process |
| POST   | `/api/apps/{id}/restart`          | Restart |
| GET    | `/api/apps/{id}/logs?lines=200`   | Tail log file |
| POST   | `/api/apps/{id}/deploy/zip`       | multipart `file=*.zip` |
| POST   | `/api/apps/{id}/deploy/git`       | Git clone or pull |

App types: `python`, `flask`, `django`, `fastapi`, `node`, `php`, `static`, `docker`.

## Files (scoped to `/var/lib/pdcloud/apps`)

| Method | Path | Description |
|---|---|---|
| GET    | `/api/files/list?path=`     | List directory |
| GET    | `/api/files/read?path=`     | Read text file |
| POST   | `/api/files/write`          | `{path, content}` |
| POST   | `/api/files/upload?path=`   | multipart `file=` |
| GET    | `/api/files/download?path=` | Download |
| DELETE | `/api/files/delete?path=`   | Delete file/folder |
| POST   | `/api/files/rename`         | `{path, new_name}` |
| POST   | `/api/files/mkdir`          | `{path, name}` |
| POST   | `/api/files/extract?path=`  | Unzip in place |

## Terminal

| Method | Path | Description |
|---|---|---|
| POST | `/api/terminal/exec`      | `{command, cwd?}` returns `{output, exit_code, cwd}` |
| GET  | `/api/terminal/history`   | Recent commands |

## Docker

| Method | Path | Description |
|---|---|---|
| GET    | `/api/docker/status`               | `{available: bool}` |
| GET    | `/api/docker/containers`           | List |
| GET    | `/api/docker/images`               | List |
| POST   | `/api/docker/containers`           | Run new container |
| POST   | `/api/docker/containers/{id}/start`   | |
| POST   | `/api/docker/containers/{id}/stop`    | |
| POST   | `/api/docker/containers/{id}/restart` | |
| DELETE | `/api/docker/containers/{id}`         | Remove |
| GET    | `/api/docker/containers/{id}/logs?tail=200` | |
| POST   | `/api/docker/compose/up`           | `{name, compose_yaml}` |
| POST   | `/api/docker/compose/{name}/down`  | |

## Databases

| Method | Path | Description |
|---|---|---|
| GET  | `/api/db/tables?path=`  | List SQLite tables |
| POST | `/api/db/query`         | `{database, sql}` — SQLite path or PG DSN |

## Backups

| Method | Path | Description |
|---|---|---|
| GET    | `/api/backups`                  | List |
| POST   | `/api/backups/panel`            | Full panel backup |
| POST   | `/api/backups/apps/{app_id}`    | App snapshot |
| GET    | `/api/backups/{id}/download`    | Download tar.gz |
| DELETE | `/api/backups/{id}`             | Delete |

## Notifications

| Method | Path | Description |
|---|---|---|
| GET  | `/api/notifications/telegram`       | Current Telegram config |
| POST | `/api/notifications/telegram`       | `{bot_token, chat_id}` |
| POST | `/api/notifications/telegram/test`  | Send test message |
