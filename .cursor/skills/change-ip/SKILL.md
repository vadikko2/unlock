---
name: change-ip
description: >-
  Change the public IPv4 of the unlock AmneziaWG VDS, update the domain A-record,
  verify DNS/reachability, and refresh GitHub deploy secrets. Use when the user
  says /change-ip, "change IP", "rotate IP", "new IP for VPN", "IP not reachable
  from home", or asks to rotate the Amsterdam VDS address for 24testreservation.ru.
---

# /change-ip — rotate public IP for unlock VDS

Project **unlock**: AmneziaWG + Cursor proxy on a Timeweb VDS in Amsterdam (`nl-1`).
VPN domain: `WG_HOST` from `.env` (default `24testreservation.ru`).

Account constants (re-check via MCP at start):

| Item | Value |
|---|---|
| Server name | `AmneziaWG` |
| Server id | `6345973` (if missing — `list_servers`) |
| Domain | `24testreservation.ru` (`WG_HOST`) |
| GitHub repo | `vadikko2/unlock` |
| SSH | `root@CURRENT_IP` (user key `~/.ssh/id_ed25519`) |

Use Timeweb MCP (`timeweb-cloud` / `search_tools` → `get_tool_definition` → `execute_tool`).
`[WRITE]` needs two-step `confirm_token`; `[BILLABLE]` — quote the price and get an explicit yes before confirm.

## Procedure (do not skip checks)

### 0. Confirm and snapshot current state

1. `list_servers` / `get_server` → current IPv4, disk id, availability zone.
2. On the server: `ip -4 addr show eth0` and `dig +short $WG_HOST`.
3. Tell the user: old IP, domain, that a new floating IP is **billed from creation**; no disk restore.
4. Confirm: allocate the new IP in the **same** location (`nl-1` / Amsterdam).

### 1. New public IP

1. Catalog / `list_floating_ips` + `create_floating_ip` in the right AZ (`[BILLABLE]` — quote + confirm).
2. Attach to server `6345973`: `bind_floating_ip` (or `add_server_ip` if that is what the account schema requires — check the tool definition).
3. Unbind the old IP only after the new one responds and DNS is updated (or on explicit user request). **Unbind ≠ delete** — the old IP keeps billing until removed in the panel.
4. Wait until the OS shows the new address:

```bash
ssh root@NEW_OR_OLD_IP 'ip -4 addr show eth0'
```

Reboot via `server_action` if needed. The new IP must appear on `eth0`.

### 2. Domain A-record

1. `get_domain_dns_records` for `24testreservation.ru` (or current `WG_HOST`).
2. Find the A-record for host `@` (or empty/root name as returned by the API).
3. `update_dns_record` → value = **new IPv4**, TTL **300**. Do **not** enable cloud/proxy.
4. Wait ~1–5 minutes, then check from the local machine and the server:

```bash
dig +short 24testreservation.ru
```

Must return the **new** IP. Do not continue until dig matches (retry dig as needed).

Leave `WG_HOST` in `.env` / `DEPLOY_ENV` unchanged (keep the domain) unless the user asked to change the domain.

### 3. Subnet reachability from home

On the server:

```bash
ping -c 2 1.1.1.1
```

Expect: `2 received`.

From the user's machine (or ask the user to run):

```bash
ping -c 3 NEW_IP
```

- `100% packet loss` → subnet blocked toward home: **reject** this IP, allocate another (`create_floating_ip` again / different subnet), update DNS again. Do not leave a dead IP in the A-record.
- `0% packet loss` → OK, continue.

### 4. GitHub secrets and deploy

1. Update secret `DEPLOY_HOST` on `vadikko2/unlock` to the new IP (`gh secret set DEPLOY_HOST -R vadikko2/unlock -b 'NEW_IP'`).
2. GitHub variables (`vars.WG_HOST`): keep domain unchanged unless a domain change was requested.
3. Trigger deploy: `gh workflow run "Deploy to VDS" -R vadikko2/unlock` (or push to master) and wait for success.
4. On the server verify:

```bash
docker compose -f /opt/unlock/docker-compose.yml ps
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:51822/
ss -tulnp | grep -E '443|1080|51822'
```

Peers in `wg show` must not reset to zero (git `wg0.json` on the bind mount).

### 5. Cursor proxy on the user machine

Cursor `settings.json` must keep the domain, never a raw IP:

```json
"http.proxy": "http://PROXY_USER:PROXY_PASSWORD@24testreservation.ru:1080"
```

After an IP change the A-record moves and this line stays. Do not tell the user to put the new IP in `http.proxy`. Fully restart Cursor only if the line itself changed.

### 6. Amnezia clients

Tell the user to toggle the tunnel off/on on phones/PCs. Endpoint stays `WG_HOST:443`; re-import is not needed if git keys are unchanged.

### 7. Final report

Return briefly:

- old IP → new IP
- domain dig result
- home ping result (or what the user must run)
- `DEPLOY_HOST` updated / deploy status
- reminder for Cursor `settings.json` and Amnezia toggle
- fate of the old IP (unbound / still billed / delete in panel)

## Anti-patterns

- Do not run a destructive disk `restore` just to change IP.
- Do not leave an A-record pointing at an IP with 100% loss from home.
- Do not set `WG_HOST` to a raw IP unless the user asked.
- Do not commit `.env` / MCP tokens.
- Do not create Amnezia clients via the web UI after an IP change — only git / `make add-client`.

## Related skills

- Timeweb IPs: `.cursor/skills/timeweb-network/SKILL.md`
- DNS: `.cursor/skills/timeweb-domains/SKILL.md`
- VDS reboot: `.cursor/skills/timeweb-servers/SKILL.md`
