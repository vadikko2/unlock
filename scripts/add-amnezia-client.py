#!/usr/bin/env python3
"""Add an AmneziaWG client to amnezia/wireguard/wg0.json (git source of truth).

Usage:
  ./scripts/add-amnezia-client.py "Имя устройства"
  ./scripts/add-amnezia-client.py "Имя" --export   # also print client config

Then commit wg0.json and push to master (GitHub Actions deploys).
Do not add clients via the web UI — it won't be in git.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WG_JSON = ROOT / "amnezia" / "wireguard" / "wg0.json"
ENV_FILE = ROOT / ".env"


def load_dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip("'").strip('"')
    return out


def wg_genkey() -> str:
    return subprocess.check_output(["wg", "genkey"], text=True).strip()


def wg_pubkey(private: str) -> str:
    return subprocess.check_output(
        ["wg", "pubkey"], input=private + "\n", text=True
    ).strip()


def wg_genpsk() -> str:
    return subprocess.check_output(["wg", "genpsk"], text=True).strip()


def next_address(clients: dict, server_address: str) -> str:
    used = set()
    m = re.match(r"^(\d+\.\d+\.\d+)\.(\d+)$", server_address)
    if not m:
        raise SystemExit(f"unexpected server address: {server_address}")
    prefix, _ = m.group(1), int(m.group(2))
    used.add(int(m.group(2)))
    for c in clients.values():
        am = re.match(r"^(\d+\.\d+\.\d+)\.(\d+)$", c.get("address", ""))
        if am and am.group(1) == prefix:
            used.add(int(am.group(2)))
    for host in range(2, 255):
        if host not in used:
            return f"{prefix}.{host}"
    raise SystemExit("no free addresses in subnet")


def export_config(server: dict, client: dict, env: dict[str, str]) -> str:
    host = env.get("WG_HOST", "24testreservation.ru")
    port = env.get("WG_PORT", "443")
    dns = env.get("WG_DEFAULT_DNS", "1.1.1.1")
    allowed = env.get("WG_ALLOWED_IPS", "0.0.0.0/0")
    mtu = env.get("WG_MTU", "1280")
    keepalive = env.get("WG_PERSISTENT_KEEPALIVE", "25")
    return "\n".join(
        [
            "[Interface]",
            f"PrivateKey = {client['privateKey']}",
            f"Address = {client['address']}/32",
            f"DNS = {dns}",
            f"MTU = {mtu}",
            f"Jc = {server['jc']}",
            f"Jmin = {server['jmin']}",
            f"Jmax = {server['jmax']}",
            f"S1 = {server['s1']}",
            f"S2 = {server['s2']}",
            f"H1 = {server['h1']}",
            f"H2 = {server['h2']}",
            f"H3 = {server['h3']}",
            f"H4 = {server['h4']}",
            "",
            "[Peer]",
            f"PublicKey = {server['publicKey']}",
            f"PresharedKey = {client['preSharedKey']}",
            f"AllowedIPs = {allowed}",
            f"Endpoint = {host}:{port}",
            f"PersistentKeepalive = {keepalive}",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="Client display name")
    parser.add_argument(
        "--export",
        action="store_true",
        help="Print Amnezia client config to stdout after adding",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be added without writing",
    )
    args = parser.parse_args()

    if not WG_JSON.exists():
        print(f"missing {WG_JSON}", file=sys.stderr)
        return 1

    data = json.loads(WG_JSON.read_text(encoding="utf-8"))
    clients: dict = data.setdefault("clients", {})
    server = data["server"]

    for c in clients.values():
        if c.get("name") == args.name:
            print(f"client already exists: {args.name}", file=sys.stderr)
            return 1

    priv = wg_genkey()
    pub = wg_pubkey(priv)
    psk = wg_genpsk()
    addr = next_address(clients, server["address"])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    cid = str(uuid.uuid4())
    client = {
        "id": cid,
        "name": args.name,
        "address": addr,
        "privateKey": priv,
        "publicKey": pub,
        "preSharedKey": psk,
        "createdAt": now,
        "updatedAt": now,
        "enabled": True,
    }

    print(f"add: {args.name} → {addr} ({cid})")
    if args.dry_run:
        return 0

    clients[cid] = client
    WG_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.chmod(WG_JSON, 0o600)
    # Drop derived conf so the container regenerates it from JSON on start
    conf = WG_JSON.with_name("wg0.conf")
    if conf.exists():
        conf.unlink()
        print(f"removed {conf.name} (regenerated on deploy)")

    print(f"updated {WG_JSON.relative_to(ROOT)}")
    print("next: git add amnezia/wireguard/wg0.json && git commit && git push")

    if args.export:
        env = load_dotenv(ENV_FILE)
        env.update({k: v for k, v in os.environ.items() if k.startswith("WG_")})
        print("\n--- client config ---")
        print(export_config(server, client, env), end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
