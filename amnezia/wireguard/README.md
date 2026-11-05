# wireguard state

`wg0.json` is committed. Per-device files live in `clients/` (gitignored).

```bash
make add-client NAME="Device"
git add amnezia/wireguard/wg0.json && git commit && git push
make send NAME="Device"    # QR downloads the .conf onto a phone
```
