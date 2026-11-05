# unlock

Docker Compose: **AmneziaWG** + **Cursor HTTP proxy (GOST)** on a VDS.

## Deploy

Push to `master` → GitHub Actions syncs to the VDS and runs `docker compose up -d --build`.

Manual run: Actions → **Deploy to VDS** → Run workflow.

Required repo secrets:

| Secret | Meaning |
|---|---|
| `DEPLOY_HOST` | VDS IP |
| `DEPLOY_USER` | SSH user (`root`) |
| `DEPLOY_SSH_KEY` | private deploy key |
| `DEPLOY_ENV` | full `.env` contents |

Server path: `/opt/unlock`.

## Services

| Service | Ports |
|---|---|
| `amnezia-wg-easy` | UDP 443, UI TCP 51822 |
| `cursor-proxy` | TCP 1080 |

Peers: панель Amnezia `http://IP:51822` (пароль из `.env` / `DEPLOY_ENV`).

## Cursor

```json
"http.proxy": "http://PROXY_USER:PROXY_PASSWORD@IP:1080",
"http.proxyStrictSSL": true,
"http.proxySupport": "override",
"cursor.general.disableHttp2": true
```
