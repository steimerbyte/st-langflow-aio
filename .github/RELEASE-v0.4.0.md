# Release v0.4.0

Mega-architektur-Switch: RHEL UBI raus, Fedora 44 rein.

## Was sich geändert hat

| | v0.3.x | v0.4.0 |
|---|--------|--------|
| Base | `langflowai/langflow:base-1.13.0.dev22` (RHEL UBI 10.2) | `fedora:44` |
| Package Manager | microdnf + manuelles Repo-Wiring | dnf (Fedora-Repos) |
| langflow-Install | in der upstream-Image eingebacken | `pip install langflow` |
| ffmpeg | DRop (kein entitlement) | native Fedora-Repo |
| chromium | DRop (kein entitlement) | native Fedora-Repo + `/usr/bin/chromium-browser` symlink auf `/usr/local/bin/chromium` |
| Image-Größe | 2.25 GB | 3.99 GB |
| Python | 3.14.7 (in UBI venv) | 3.14.7 (Fedora system) |

## Warum der Switch

langflowai/langflow hat ab 1.11+ das Base-Image von Debian auf RHEL UBI 10.2
umgestellt. UBI ohne bezahlte RHEL-Subscription kann `libSDL2-2.0.so.0` und
`libpipewire-0.3.so.0` nicht auflösen — ffmpeg und chromium sind dadurch nicht
installierbar. Auch RPM Fusion + CentOS-Stream-Hacks helfen nicht (siehe v0.3.2).

Fedora 44 hat:

- ffmpeg + chromium direkt im Default-Repo (kein RPM Fusion nötig)
- Python 3.14.7 mit allen Wheels für pandas, lxml, etc.
- Node 22, git, curl, build-toolchain

## MiniMax-Integration unverändert

Die Provider-Registry-basierte Registrierung aus v0.3.x bleibt. Dieselben
Skripte (`inject/register_minimax.py`, `inject/sitecustomize.py`,
`inject/verify_inplace.py`) — mit Anpassung an Fedora's `lib64/`-Layout der
venv.

## Migration von v0.3.x

```bash
git pull
cd /home/docker/st-langflow-aio
docker compose down
docker build --no-cache -t st-langflow-aio:latest .
docker compose up -d
docker exec -it $(docker ps -qf name=langflow) python3 /tmp/verify_inplace.py
docker exec -it $(docker ps -qf name=langflow) ffmpeg -version | head -1
docker exec -it $(docker ps -qf name=langflow) chromium-browser --version
```

## Persistenz

Alle installierten Binaries leben in Image-Layern. Überleben jeden Container-
Neustart und jeden `docker compose down/up`. Postgres-Daten (`/home/docker/langflow/postgres/`)
und Flow-Daten (`/home/docker/langflow/data/`) bleiben wie gehabt auf Host-Volumes.
