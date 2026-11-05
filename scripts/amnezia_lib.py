"""Shared Amnezia client config export. Not a CLI."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WG_JSON = ROOT / "amnezia" / "wireguard" / "wg0.json"
ENV_FILE = ROOT / ".env"
CLIENTS_DIR = ROOT / "clients"


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


def env() -> dict[str, str]:
    data = load_dotenv(ENV_FILE)
    data.update({k: v for k, v in os.environ.items() if k.startswith("WG_")})
    return data


def export_config(server: dict, client: dict, values: dict[str, str]) -> str:
    host = values.get("WG_HOST", "24testreservation.ru")
    port = values.get("WG_PORT", "443")
    dns = values.get("WG_DEFAULT_DNS", "1.1.1.1")
    allowed = values.get("WG_ALLOWED_IPS", "0.0.0.0/0")
    mtu = values.get("WG_MTU", "1280")
    keepalive = values.get("WG_PERSISTENT_KEEPALIVE", "25")
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


def safe_name(name: str) -> str:
    cleaned = name.replace("/", "-").replace("\x00", "").strip()
    if not cleaned or cleaned in {".", ".."}:
        raise SystemExit(f"bad client name: {name!r}")
    return cleaned


def write_client_file(name: str, text: str) -> Path:
    CLIENTS_DIR.mkdir(mode=0o700, exist_ok=True)
    path = CLIENTS_DIR / f"{safe_name(name)}.conf"
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o600)
    return path
