#!/usr/bin/env python3
"""Print Amnezia client config from git-tracked wg0.json.

Usage:
  ./scripts/export-amnezia-client.py "Вадим IPhone"
  ./scripts/export-amnezia-client.py --list
"""
from __future__ import annotations

import argparse
import json
import os
import sys
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
    parser.add_argument("name", nargs="?", help="Client name")
    parser.add_argument("--list", action="store_true", help="List clients")
    args = parser.parse_args()

    data = json.loads(WG_JSON.read_text(encoding="utf-8"))
    clients = data.get("clients") or {}

    if args.list or not args.name:
        for c in sorted(clients.values(), key=lambda x: x.get("address", "")):
            print(f"{c.get('address')}\t{c.get('name')}\tenabled={c.get('enabled')}")
        return 0 if args.list or not args.name else 1

    match = [c for c in clients.values() if c.get("name") == args.name]
    if not match:
        print(f"not found: {args.name}", file=sys.stderr)
        return 1

    env = load_dotenv(ENV_FILE)
    env.update({k: v for k, v in os.environ.items() if k.startswith("WG_")})
    print(export_config(data["server"], match[0], env), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
