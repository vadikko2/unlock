#!/usr/bin/env python3
"""Write clients/<name>.conf from git-tracked wg0.json.

Usage:
  ./scripts/export-amnezia-client.py --list
  ./scripts/export-amnezia-client.py "Name"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from amnezia_lib import ROOT, WG_JSON, env, export_config, write_client_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", nargs="?", help="Client name")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    data = json.loads(WG_JSON.read_text(encoding="utf-8"))
    clients = data.get("clients") or {}

    if args.list or not args.name:
        for c in sorted(clients.values(), key=lambda x: x.get("address", "")):
            print(f"{c.get('address')}\t{c.get('name')}\tenabled={c.get('enabled')}")
        return 0

    match = [c for c in clients.values() if c.get("name") == args.name]
    if not match:
        print(f"not found: {args.name}", file=sys.stderr)
        return 1

    text = export_config(data["server"], match[0], env())
    conf = write_client_file(args.name, text)
    print(f"file: {conf.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
