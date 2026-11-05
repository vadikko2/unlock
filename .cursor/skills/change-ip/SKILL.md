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
`[WRITE]` needs two-step `confirm_token`. `[BILLABLE]` — read the live price from `operation_summary` and get an explicit yes before the confirming call. Do not quote a price from memory.

Do these five steps in order. Do not change DNS until step 2 passed. Do not unbind the old address until step 4 shows the new one.

## 1. Get a new IP from a different subnet

1. `get_server` / `list_floating_ips` and `ip -4 addr show eth0` on the box. Note the current primary (DHCP `/24`), its gateway (`ip route`), and the floating-IP UUID.
2. `create_floating_ip` in the server's zone (`ams-1`), `is_ddos_guard: false`. The tool cannot pick a prefix. It only picks the zone. The summary names the monthly price (plain `floating_ip` in this zone). The address is billed from creation, bound or not, and MCP cannot delete it.
3. Reject the result when its `/24` is the same as the current primary. Say so and stop this run rather than pointing DNS at the blocked prefix.
4. `bind_floating_ip` to server `6345973`. `get_server` must list the new IPv4 (`is_main: false` is expected). Binding does not configure the guest.

At most two paid addresses per run. After two different prefixes fail step 2, stop. Unbind every failed address in that same run (see below). Do not leave it on the server.

## 2. Put that IP on the machine and prove it works

Binding, a guest-agent restart, and a reboot do **not** add the address to `eth0`. Cloud-init DHCP stays on the old `/24`. Do not set `dhcp4: false` and do not replace `50-cloud-init.yaml`.

On the server, add the address as `/32` (the hypervisor routes it to this NIC; a second gateway is not required while the old default route exists):

```bash
ip addr add NEW/32 dev eth0
ping -c 2 -W 2 -I NEW 1.1.1.1
```

`2 received` means the host may send from the new source through the current gateway. Then make it survive reboot. New file, mode `600` (netplan skips a world-readable file):

```yaml
# /etc/netplan/60-unlock-extra-ips.yaml
network:
  version: 2
  ethernets:
    eth0:
      addresses:
        - "NEW/32"
```

`chmod 600` that file, then `netplan generate && netplan apply`. SSH to the old IP must still work afterwards. `ip -4 addr show eth0` must show both the DHCP primary and `NEW/32`.

Then three reachability checks. All three are required.

1. **Another network, not the user's LAN.** From another account VDS (the SPb box `85.193.91.121` if the user key logs in): `ping -c 2 NEW`. `0% loss` means the fabric delivers this address to the VM. `100% loss` means the guest or the bind is wrong — fix that, do not call it a blocked subnet.
2. **The user's machine, off the tunnel.** `route -n get NEW` must show `en0` and the LAN gateway. A default route via `utun` hairpins through Amnezia and lies. Then `ping -c 3 NEW` and `nc -z -G 4 NEW 22`.
3. **If the home ping fails, capture on the server during that ping:** `timeout 8 tcpdump -n -i eth0 host NEW -c 6`.
   - `0 packets` while check 1 succeeded: this path drops the prefix. Do not change DNS.
   - Packets arrive and nothing answers: fix the guest, then retest.

Home Wi-Fi answering the old `/24` does not mean a new prefix works, and it does not mean mobile carriers will accept it. If this rotation is because mobile networks block the current prefix, ask the user to ping `NEW` from the phone before step 3. Never move the A-record to an address the home machine cannot ping.

On 2026-11-05 the primary `179.252.208.227/24` answered from home Wi-Fi. Two other Amsterdam prefixes (`64.188.62.238`, `147.45.238.50`) answered from the SPb VDS and from the box itself (`ping -I`), and from home Wi-Fi both ICMP and TCP/22 were dead with zero frames on `eth0`. DNS stayed on the old address. Both failed addresses were then unbound; `get_floating_ip` returned not found, so there was nothing left to delete.

When step 2 fails, clean the guest and unbind before you stop:

```bash
ip addr del NEW/32 dev eth0
# drop that address from /etc/netplan/60-unlock-extra-ips.yaml, or remove the file if it is the only one
netplan generate && netplan apply
```

Then `unbind_floating_ip` for that UUID. Check `get_floating_ip` afterwards.

- Not found: the address is gone from the account. Do not tell the user to delete it.
- Still listed, unbound: say so in the reply, with the address and UUID. Deletion is not in MCP (`delete_floating_ip` is not exposed). The user deletes it at https://timeweb.cloud/my . Unbind does not by itself stop the charge while the address still exists. Do not describe panel clicks.

## 3. Point the A-record at the new IP

Only after step 2 passed from home (ping `0%` and TCP/22 or UDP/443).

1. `get_domain_dns_records` for `WG_HOST`.
2. Update the root A-record (`update_dns_record`, PUT: resend the fields you must keep). Value = new IPv4, TTL `300`. Do not enable a cloud proxy.
3. Leave `WG_HOST` as the domain. Do not write a raw IP into `.env` or GitHub variables.

## 4. Check dig

From the Mac and from the server:

```bash
dig +short 24testreservation.ru
```

Retry for a few minutes. Continue only when both answers are exactly the new IP. Then:

1. `gh secret set DEPLOY_HOST -R vadikko2/unlock -b 'NEW_IP'`.
2. `gh workflow run "Deploy to VDS" -R vadikko2/unlock` and wait until it is green.
3. On the server: `docker compose -f /opt/unlock/docker-compose.yml ps`, Amnezia UI `http://127.0.0.1:51822/` returns a code, `ss` shows UDP `443` and TCP `1080`/`51822`, `wg show` peer count is not zero.
4. SSH to `root@NEW` from home must succeed before step 5. Cursor `http.proxy` stays on the domain, not the new IP. Tell the user to toggle Amnezia off/on; the endpoint stays `WG_HOST:443`.

## 5. Unbind the old IP, then delete it

Do this only after step 4 and only for the previous primary. Failed candidates are already unbound in step 2.

The primary is DHCP on the old `/24`, and the default route uses that gateway. Before `unbind_floating_ip`:

- Keep an on-link route to the current gateway and a default route that still works with source `NEW`.
- Confirm `ping -I NEW -c 2 1.1.1.1` and SSH to `NEW` one more time.

Then `unbind_floating_ip` on the old UUID. SSH to `NEW` again. `ip -4 addr` must still have `NEW/32`, and `ping -c 2 1.1.1.1` must get 2 replies. If the box does not come back, `bind_floating_ip` the old UUID again.

`search_tools("delete floating ip")` returns not-exposed (`delete_floating_ip` is panel-only). After unbind, call `get_floating_ip`. If it is not found, the address is already gone. If it is still on the account, the reply must list that address and UUID and tell the user to delete it at https://timeweb.cloud/my . Do not describe panel clicks. Do not claim the charge stopped while the address still exists.

## Report

- old IP → new IP, and any rejected addresses that are still billed
- home ping and TCP result, plus the outside-vantage ping
- `dig` result
- `DEPLOY_HOST` and deploy status
- Cursor line unchanged (domain); Amnezia toggle
- which addresses were unbound, which `get_floating_ip` no longer finds, and which address plus UUID the user still has to delete

## Anti-patterns

- Do not run a disk `restore` to change an IP.
- Do not change the A-record, `DEPLOY_HOST`, or the old binding when home ping/TCP to the new address fails.
- Do not treat a reboot as the way to install an extra floating IP.
- Do not order a third paid IP in the same run after two prefixes fail from home.
- Do not leave a rejected address bound to the server. Unbind it in the same run.
- Do not set `WG_HOST` or `http.proxy` to a raw IP unless the user asked.
- Do not commit `.env` or MCP tokens.
- Do not create Amnezia clients in the web UI — only git / `make add-client`.

## Related skills

- Timeweb IPs: `.cursor/skills/timeweb-network/SKILL.md`
- DNS: `.cursor/skills/timeweb-domains/SKILL.md`
- VDS reboot: `.cursor/skills/timeweb-servers/SKILL.md`
