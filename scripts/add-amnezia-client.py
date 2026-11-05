#!/usr/bin/env python3
"""Add an AmneziaWG client to amnezia/wireguard/wg0.json and write clients/<name>.conf.

Then commit wg0.json and push to master so the peer lands on the VDS.
Hand the file over with `make send NAME=...` (qrcp). Do not commit clients/.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from amnezia_lib import WG_JSON, ROOT, env, export_config, write_client_file  # noqa: E402

import re
import subprocess


def wg_genkey() -> str:
    return subprocess.check_output(["wg", "genkey"], text=True).strip()


def wg_pubkey(private: str) -> str:
    return subprocess.check_output(["wg", "pubkey"], input=private + "\n", text=True).strip()


def wg_genpsk() -> str:
    return subprocess.check_output(["wg", "genpsk"], text=True).strip()


def next_address(clients: dict, server_address: str) -> str:
    used = set()
    m = re.match(r"^(\d+\.\d+\.\d+)\.(\d+)$", server_address)
    if not m:
        raise SystemExit(f"unexpected server address: {server_address}")
    prefix = m.group(1)
    used.add(int(m.group(2)))
    for c in clients.values():
        am = re.match(r"^(\d+\.\d+\.\d+)\.(\d+)$", c.get("address", ""))
        if am and am.group(1) == prefix:
            used.add(int(am.group(2)))
    for host in range(2, 255):
        if host not in used:
            return f"{prefix}.{host}"
    raise SystemExit("no free addresses in subnet")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="Client display name")
    parser.add_argument("--dry-run", action="store_true")
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
            print("re-export: make export-client NAME=...   then  make send NAME=...", file=sys.stderr)
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

    print(f"add: {args.name} → {addr}")
    if args.dry_run:
        return 0

    clients[cid] = client
    WG_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(WG_JSON, 0o600)
    derived = WG_JSON.with_name("wg0.conf")
    if derived.exists():
        derived.unlink()

    text = export_config(server, client, env())
    conf = write_client_file(args.name, text)
    print(f"file: {conf.relative_to(ROOT)}", file=sys.stderr)
    print("server: git add amnezia/wireguard/wg0.json && git commit && git push", file=sys.stderr)
    print("phone:  make send NAME=%r" % args.name, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
