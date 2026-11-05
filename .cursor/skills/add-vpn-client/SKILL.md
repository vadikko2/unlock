---
name: add-vpn-client
description: >-
  Add an AmneziaWG client, push it to master, confirm the VDS deploy, and
  print a qrcp QR so a phone can download the .conf. Use when the user says
  "add client", "new vpn config", "make add-client", "make send", or asks
  how a phone gets a tunnel config. The agent pushes and verifies; it does
  not hand those steps back to the user.
---

# Add an Amnezia client, deploy it, show the download QR

Source of truth is `amnezia/wireguard/wg0.json`. The phone downloads `clients/<name>.conf` via qrcp. Do not print a QR of the config body.

Do the whole path yourself. Do not stop after writing the file and ask the user to commit, push, or run `make send`.

## Steps

1. Create the peer (`wg` from wireguard-tools). If the name already exists, stop and say so. Do not add a second peer with the same name.

```bash
make add-client NAME="Device name"
```

This updates `wg0.json` and writes `clients/<name>.conf` (mode 600). Never `git add clients/`.

2. Push to `master` yourself:

```bash
git add amnezia/wireguard/wg0.json
git commit -m "feat: add amnezia client Device name"
git push origin master
```

3. Confirm delivery before showing the QR. Watch the **Deploy to VDS** run for that push until it succeeds (`gh run watch` on `vadikko2/unlock`). The run SSHs to `DEPLOY_HOST`. That host is the current VPS, which may be 62yun or Timeweb; do not assume the old Timeweb box. A failed run means the new peer is not on that server: fix or report it, and do not tell the user the tunnel is ready. On success, the workflow log prints the peer count from `wg show`. The phone still has to import the file; the endpoint in it is the domain, so a later IP change does not need a new config.

4. Show the download QR. `qrcp` must be installed (`brew install qrcp` if `qrcp` is missing). Run this and leave it running so the QR stays on screen:

```bash
make send NAME="Device name"
```

The QR is qrcp's, for downloading the `.conf` onto a phone on the same Wi-Fi. Tell the user to scan it, then forward the file; Amnezia imports a file, not this QR. Ctrl+C stops the server. Wrong network: `make send NAME="..." IFACE=en1` (default `en0`).

## Do not

- Ask the user to push or to run `make send` themselves.
- Print a config-body QR. There is no `make qr`.
- Commit `clients/` or `.env`.
- Create the client in the Amnezia web UI.
- Claim the phone can connect before the deploy run is green.
