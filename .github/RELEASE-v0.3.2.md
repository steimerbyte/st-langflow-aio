# Release v0.3.2

Restore ffmpeg + chromium via RPM Fusion and EPEL on RHEL UBI 10.2.

## What changed since v0.3.1

v0.3.0/0.3.1 dropped ffmpeg and chromium because the langflow base image
switched to **RHEL UBI 10.2** in 1.11+ — neither package is in the UBI default
repos. v0.3.2 re-enables them by installing:

- **RPM Fusion free** (`rpmfusion-free-release-10.noarch.rpm`) — provides `ffmpeg`
- **EPEL** (`epel-release-latest-10.noarch.rpm`) — provides `chromium`

Both repo RPMs are pulled at build time and registered with `rpm -i`. After
they land, `microdnf install -y ffmpeg chromium ...` resolves successfully.

Also added the puppeteer system libs (`libgbm`, `libxkbcommon`, `libdrm`,
`libXcomposite`, `libXdamage`, `libXrandr`, etc.) that chromium needs at
runtime, plus `PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium` so langflow's
puppeteer-based components find the binary.

Image size grows by ~150 MB.

## Migration from v0.3.1

Same as v0.3.1. No data migration.

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
docker exec -it $(docker ps -qf name=langflow) ffmpeg -version | head -1
docker exec -it $(docker ps -qf name=langflow) command -v chromium
```
