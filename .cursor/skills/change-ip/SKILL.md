---
name: change-ip
description: >-
  Move or rotate the public IPv4 of the unlock VPN (AmneziaWG + Cursor proxy).
  The VPS may be on 62yun or Timeweb. DNS for 24testreservation.ru stays on
  Timeweb either way. Use when the user says /change-ip, "change IP",
  "rotate IP", "new IP for VPN", "move the server", or "switch the domain".
---

# /change-ip — point the VPN at a working address

The stack is Docker Compose in `/opt/unlock`. Clients live in git (`amnezia/wireguard/wg0.json`). `WG_HOST` stays the domain. `DEPLOY_HOST` is the IP GitHub Actions SSH to. Cursor `http.proxy` stays on the domain.

DNS for `24testreservation.ru` is always Timeweb (`update_dns_record`), even when the VPS is not.

## Where things are (re-check, do not trust a stale IP)

| Role | Current value |
|---|---|
| Live VPS | 62yun, panel id `194815`, name `svr_194815`, Ubuntu 24.04, Dronten. IPv4 `199.246.126.45`, NIC `ens192`, gateway `199.246.126.1` |
| 62yun panel | https://62yun.ru/servers/control/index/194815 — browser session only, no API |
| DNS | Timeweb zone `24testreservation.ru`. Authoritative check: `dig +norecurse 24testreservation.ru A @85.193.93.93` |
| GitHub | `vadikko2/unlock`. Secrets `DEPLOY_HOST`, `DEPLOY_USER` (`root`), `DEPLOY_SSH_KEY` |
| SSH keys on the box | user `~/.ssh/id_ed25519` and repo `.deploy-keys/gha_deploy` |
| Old Timeweb VPS | `AmneziaWG` id `6345973`, `179.252.208.227`, `nl-1`. Not the deploy target while `DEPLOY_HOST` is the 62yun address. It keeps billing until the user removes it |

`gh` on this Mac is `/opt/homebrew/Cellar/gh/2.102.0/bin/gh` when it is missing from `PATH`.

Read `ssh root@$DEPLOY_HOST 'ip -4 addr; ip route'` and `dig +short` first. The host is whichever of those two answers. Do not order a Timeweb floating IP when the live box is 62yun.

## Order

Do not change the A-record until the new address is on the machine and home can deliver packets to it. Do not tell the user to reconnect Amnezia until authoritative DNS shows the new IP.

### 1. Get the address onto a machine

**Same 62yun VPS, new address.** There is no API. In the panel use "Заменить IP-адрес". The guest learns it by DHCP on `ens192`. Do not add a `/32` by hand and do not use the Timeweb floating-IP flow. SSH to the new address, then set `DEPLOY_HOST` to it.

**New 62yun VPS (what happened on 2026-11-05).** The panel root password is in the page markup, not in chat. Use it once, then install keys and stop using the password:

- `~/.ssh/id_ed25519.pub` and `.deploy-keys/gha_deploy.pub` into `/root/.ssh/authorized_keys` (`700` / `600`)
- Docker Engine and the Compose plugin, if `docker compose version` fails. `modprobe tun`
- `gh secret set DEPLOY_HOST -R vadikko2/unlock -b 'NEW_IP'`
- `gh workflow run "Deploy to VDS" -R vadikko2/unlock` and wait until the run is green
- Peer count from `wg show` must not be zero. `wg0.json` arrives with the deploy. Do not recreate clients in the web UI

**Timeweb VPS only.** `create_floating_ip` in the server zone (`ams-1` for `6345973`), `is_ddos_guard: false`. Quote the price from `operation_summary` and get an explicit yes. The tool cannot pick a prefix. Reject a `/24` that matches the blocked primary. `bind_floating_ip` does not configure the guest: `ip addr add NEW/32 dev eth0`, persist in `/etc/netplan/60-unlock-extra-ips.yaml` mode `600`, leave DHCP on `50-cloud-init.yaml` alone. A reboot does not install the extra address. At most two paid addresses per run. Unbind a failed one in that same run (`unbind_floating_ip`), `ip addr del` it, then `get_floating_ip`. Not found means it is gone. If it is still listed, the reply names the address and UUID; deletion is panel-only at https://timeweb.cloud/my .

### 2. Prove the address works while it is on the NIC

Checks after the address is unattached prove nothing. On 2026-11-05 a traceroute to already-unbound addresses died in the same place as a live block.

From the Mac, off the tunnel. `route -n get NEW` must show `en0` and `192.168.0.1`. A `utun` default route hairpins through Amnezia.

```bash
traceroute -n -w 2 -m 12 -q 1 NEW
nc -z -G 5 NEW 1080
nc -z -G 5 NEW 51822
```

This home ISP is `192.168.0.1` → `10.150.162.1` → `10.148.252.13` → `89.223.47.17`. If traceroute never passes `10.148.252.13`, the ISP dropped the prefix. That happened for Timeweb Amsterdam prefixes `64.188.62.238`, `147.45.238.50`, `72.56.101.17`, `216.57.110.242`, and `201.34.144.129`. Do not put those in DNS. `199.246.126.45` passed that hop.

ICMP loss is not enough. 62yun answered SSH, TCP `1080`, and TCP `51822` while ping was silent. On the server, during the home probe, capture the real NIC (`ens192` on 62yun, `eth0` on Timeweb):

```bash
tcpdump -n -i NIC -w /tmp/cap.pcap host NEW
```

A UDP datagram from the Mac to port `443` must show the home public address (this LAN was `31.134.187.175`). Also `ping -c 2 NEW` from another server (SPb `85.193.91.121` if the user key works). `0` packets from home while that other server gets replies means this path drops the prefix.

If the rotation is because mobile carriers block the current prefix, ask for a ping from the phone before DNS. Home success does not prove mobile success.

### 3. Timeweb A-record

Only after step 2. `get_domain_dns_records` for `24testreservation.ru`, then `update_dns_record` on the root A (PUT: resend fields you must keep). Value = new IPv4, TTL `300`. No cloud proxy. Leave `WG_HOST` as the domain.

The API can return the new value while the nameservers still serve the old one. On 2026-11-05 that gap was about six minutes, and the SOA serial did not move until the zone published. Keep checking:

```bash
dig +norecurse 24testreservation.ru A @85.193.93.93
dig +short 24testreservation.ru A
```

Continue only when the authoritative answer is the new IP. A local resolver may keep the previous TTL (the old record was 600 seconds). Timeweb's own docs allow up to a few hours, rarely a day.

### 4. After dig matches

`DEPLOY_HOST` must already be the new IP before this, otherwise the next push deploys to the old box. If the secret was set in step 1, do not set it again.

Tell the user to toggle Amnezia off/on. The endpoint stays `WG_HOST:443`. Keys are not reissued.

Cursor `http.proxy` stays `http://PROXY_USER:PROXY_PASSWORD@24testreservation.ru:1080` with `http.proxySupport: override` and `cursor.general.disableHttp2: true`. Do not write the new IP into settings. A full quit (Cmd+Q) is required: live sockets stay on the old proxy IP until the process exits.

Do not power off the previous VPS unless the user asks. Say which machine is still billed.

### 5. Release the old address

62yun replace drops the previous address with the panel action. There is nothing to unbind.

Timeweb: unbind only the previous primary, and only after SSH to the new address works. The DHCP default route uses the old gateway, so confirm `ping -I NEW -c 2 1.1.1.1` before `unbind_floating_ip`. If the box disappears, bind the old UUID again. Then `get_floating_ip` and list any address the user still has to delete.

## Report

- which host (62yun or Timeweb), old IP → new IP
- traceroute past `10.148.252.13` or not, and whether home UDP `443` arrived while the address was on the NIC
- authoritative dig and local dig
- deploy run and peer count
- Cursor line unchanged; Amnezia toggle; anything still billed

## Anti-patterns

- Do not create a Timeweb floating IP to fix a 62yun server.
- Do not judge an address that is already unbound.
- Do not treat ping loss alone as a dead 62yun host.
- Do not change the A-record when home packets never reach the NIC.
- Do not tell the user to reconnect before authoritative DNS matches.
- Do not set `WG_HOST` or `http.proxy` to a raw IP.
- Do not commit `.env`, MCP tokens, or the panel root password.
- Do not create Amnezia clients in the web UI.

## Related skills

- DNS: `.cursor/skills/timeweb-domains/SKILL.md`
- Timeweb IPs, only when the VPS is Timeweb: `.cursor/skills/timeweb-network/SKILL.md`
- Timeweb VDS reboot, same condition: `.cursor/skills/timeweb-servers/SKILL.md`
