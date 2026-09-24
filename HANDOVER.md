# Handover — st-langflow-aio Modernisierung

**Datum:** 2026-09-24, Session ca. 09:00–15:47 UTC
**Server-Bezug:** pve-docker (192.168.179.78), Auth-Fehler seit ~10:19 UTC, Stand 15:47 weiterhin nicht erreichbar
**Repo:** https://github.com/steimerbyte/st-langflow-aio
**Working Copy:** `/home/steimerbyte/st-langflow-aio`

---

## TLDR

Langflow auf pve-docker sollte von der alten Debian-Patch-Variante auf eine **Fedora-46-basierte v0.4.0-Image-Variante** gehoben werden. Die Architektur-Refaktorierung (Provider-Registry statt 5-File-String-Patching) ist committed und sauber. Der **Docker-Build auf Fedora 46 wurde gestartet, aber durch einen Server-Crash unterbrochen** — `st-langflow-aio:latest` ist auf dem Server eine Mischung aus früheren/v0.3.x-Ständen. Postgres-Volumen und Flow-Daten auf dem Server sind unangetastet.

Beim Wiederherstellen der Konnektivität: Server ist per Proxmox-Cycle neu zu starten, Build einmal durchziehen (~5 min, Cache teils warm), Compose hochfahren, Registry-/ffmpeg-/chromium-Verifikation laufen lassen.

---

## Session-Verlauf (chronologisch)

### 1. Status-Check langflow
- pve-docker Stack `lang-flow` (= `/home/docker/dockhand/stacks/Homelab/lang-flow/`) lief auf `langflow-pfy:latest` (uralter Stand, Container `exited` seit 2 Monaten)
- Bekannter Fehler im alten Image: `psycopg.OperationalError: failed to resolve host 'postgres'` — der Postgres-Service war in einem früheren Bridge-Network und nicht mehr unter `postgres:5432` erreichbar

### 2. Repo-Klon + Refactor
- `git clone https://github.com/steimerbyte/st-langflow-aio` lokal + server
- Stand: main auf Tag `v0.2.3`, Repo aktuell + clean
- Architektur-Refactor: alte `inject/patch_full_provider.py` (244 Zeilen String-Replace-Patching) gelöscht, ersetzt durch:
  - `inject/register_minimax.py` — `ProviderDescriptor` + `catalog_loader` gegen offizielles `lfx.base.models.provider_registry.register_provider()`
  - `inject/sitecustomize.py` — Python-Startup-Auto-Register
  - `inject/verify_inplace.py` — verifiziert 7 Registry-States
  - `inject/lfx_components/.../minimax.py` — bleibt als Side-LCModelComponent für Custom-Component-Pfad
- Net diff: **−365 Zeilen**, dabei Funktionserweiterung und Upgrade-Toleranz gegen Upstream-Refactors

### 3. Versions-Tags + Releases
- `v0.3.0` (e21b979) — initialer Refactor
- `v0.3.1` (cc2f780) — Bug-Fix: `catalog_loader` muss `list` zurückgeben, kein `tuple` (Upstream-Assertion sonst stille `TypeError`)
- `v0.3.2` (2f7c0ff, dann reverted) — erfolgloser Versuch, ffmpeg+chromium via RPM Fusion + EPEL nachzurüsten, reverted wegen RHEL-Entitlement-Gating
- `v0.4.0` (zuletzt 65b8ce5) — RHEL-Base komplett rausgeworfen, Fedora 46 + `pip install langflow`

### 4. RHEL-Discovery
- Dockerfile-`FROM langflowai/langflow:latest` produzierte ab 1.11+ `langflowai/langflow:base-1.13.0.dev22` als neues Base-Image
- base ist **Red Hat UBI 10.2** (war vorher Debian/Ubuntu), kein `apt-get`, sondern `microdnf`
- Kein `librhsm`-Entitlement in UBI-Default-Image → `libSDL2-2.0.so.0` (für ffmpeg) und `libpipewire-0.3.so.0` (für chromium) nicht auflösbar
- Auch RPM-Fusion + CentOS-Stream-Hacks (extras / baseos / appstream) liefern die libs auf subscription-losem UBI nicht

### 5. Mega-Hack: Wechsel auf Fedora 46
- User-Direktive: „yeete alle RHEL urls und repos aus dem image und replace alles mit fedora serve"
- `FROM fedora:46`, alles via `dnf install`
- Problem: Fedora 46 hat **Python 3.15** mit `setuptools ≥ 81`, das `pkg_resources` nicht mehr bündelt → pandas/lxml-Source-Builds crashen mit `ModuleNotFoundError: No module named 'pkg_resources'`
- Behoben in HEAD mit `'setuptools<81' wheel` + `--no-build-isolation`
- Build war gestartet zum Zeitpunkt des Server-Crashes, daher **nie vollständig durchgelaufen**

### 6. Server unerreichbar
- Letzter erfolgreicher SSH: ~10:13 UTC, Container wurde gestartet (Up 12 sec)
- Compose-Befehl brachte teilweise Container, dann gegen 10:16–10:17 baute ein neuer Build, der genau zum FROM-Cache-Wechsel Zeitfenster den Container stoppte
- Ab ~10:19 UTC: ping timeout, ssh connection timeout — kein „Connection refused" (spricht gegen bewusste Abschaltung), sondern Netzwerk- oder Host-Crash
- 15:47 UTC: weiterhin nicht erreichbar

---

## Aktueller Stand

### Code (alle Änderungen committed + gepusht)

| Pfad | Status |
|------|--------|
| `main` Branch | `65b8ce5` — Fedora 46, setuptools-Fix |
| `v0.3.0` | e21b979 — initialer Registry-Refactor, kaputt (FROM=:latest ohne Apt-Compat) |
| `v0.3.1` | cc2f780 — Catalog-loader list/tuple Fix, dann RHEL-Build versucht |
| `v0.3.2` | 2f7c0ff (reverted) — erfolgloser ffmpeg/chromium-Versuch |
| `v0.4.0` | 65b8ce5 — Fedora-Architekturwechsel |

### Releases (auf GitHub)

- https://github.com/steimerbyte/st-langflow-aio/releases/tag/v0.3.0 — Refactor Release-Notes
- https://github.com/steimerbyte/st-langflow-aio/releases/tag/v0.3.1 — RHEL-Build-Fix Notes
- https://github.com/steimerbyte/st-langflow-aio/releases/tag/v0.3.2 — ffmpeg/chromium deferred (UBI entitlement gap), verworfen
- https://github.com/steimerbyte/st-langflow-aio/releases/tag/v0.4.0 — Fedora 44/46 base, noch nicht live-verifiziert

### Server (pve-docker)

| Komponente | Status |
|-----------|--------|
| Compose-Datei `lang-flow/compose.yaml` | `image: st-langflow-aio:latest` ✓ (war zuvor `langflow-pfy:latest`, per sed ersetzt) |
| Repo `/home/docker/st-langflow-aio` | `git reset --hard origin/main` ausgeführt, HEAD = `65b8ce5` |
| Postgres-Daten `/home/docker/langflow/postgres/` | unangetastet, 98 MB, auf Volume |
| Flow-Daten `/home/docker/langflow/data/` | unangetastet, 3.3 MB, auf Volume |
| Container `lang-flow-langflow-1` | letzte Aktion `Recreated` mit altem v0.3.x-Image, dann absturz während eines weiteren Rebuild-Versuchs |
| Container `lang-flow-postgres-1` | wurde im Verlauf gestoppt + entfernt, beim nächsten `up -d` aus Image neu erstellt; Daten via Host-Volume erhalten |
| `st-langflow-aio:latest` Image | letzter erfolgreicher Build war v0.3.1 (Registry klappt, ohne ffmpeg/chromium). Fedora-46-Builds von v0.4.0 wurden gestartet, aber nicht fertig |

### Image-Inventar (laut letztem funktionierenden v0.3.1 Build vor dem Crash)

| Binary | Pfad | OK? |
|--------|------|-----|
| `python3` | `/app/.venv/bin/python3` (3.14.7 via langflow venv) | ja |
| `yt-dlp` | `/app/.venv/bin/yt-dlp` | ja |
| `node` | `/usr/local/bin/node` (v20.19.5) | ja |
| `npm` | `/usr/local/bin/npm` | ja |
| `langflow` | `/app/.venv/bin/langflow` | ja |
| MiniMax Registry | `is_registered('MiniMax') == True`, 8 Modelle im Catalog | ja |
| `ffmpeg` | – | **fehlt** |
| `chromium` | – | **fehlt** |

In v0.4.0 (wenn Build durchläuft): sollte ffmpeg + chromium dazukommen.

---

## Warum dieser Architektur-Wechsel nötig war

Kurzfassung der Bugs, die in langflowai/langflow seit 1.11 aufgefallen sind:

1. **Base-Image-Wechsel Debian → RHEL UBI 10.2**:
   - `apt-get` existiert nicht mehr
   - Default `microdnf`-Repos haben keine Community-Pakete
   - Subscription-gebundene Libs (`libSDL2`, `libpipewire`) unter UBI ohne Entitlements nicht installierbar
   - Auch RPM-Fusion + EPEL reichen nicht, weil sie über die fehlenden Libs transitive Deps ziehen

2. **Provider-Patching zerbricht auf neuen Upstream-Versionen**:
   - Anchor-Strings wie `WATSONX_MODELS_DETAILED,\n]` und `elif provider == "OpenRouter":\n…\n    try:` ändern sich zwischen Releases
   - Lösung: offizielles `provider_registry.register_provider()` benutzen — die machen genau diese Migration überflüssig, weil sich der Core um die Verkabelung kümmert

3. **`catalog_loader` muss eine `list` returnieren, kein `tuple`** — sonst stille `TypeError`, die `get_models_detailed()` schluckt und den Provider leer im Catalog hinterlässt (gefixt in v0.3.1)

---

## Recovery-Anleitung

### 1. Server wiederbeleben

```bash
# Proxmox-UI → Container pve-docker → Power Cycle oder via pve-shell:
# pct stop <vmid>; pct start <vmid>
# danach SSH testen
ssh root@pve-docker hostname
```

Wenn `librhsm-WARNING: Found 0 entitlement certificates` o.ä. unauffällig ist und der Kernel nicht selbst im OOM ist, sollte das harmlos sein.

### 2. Repo aktualisieren + Docker bauen + Stack hochfahren

```bash
ssh root@pve-docker <<'REMOTE'
set -euo pipefail
cd /home/docker/st-langflow-aio
git fetch origin
git reset --hard origin/main
# Image bauen — Cache teils warm (Postgres-Daten-Layer bleibt!), reicht ~5 min
docker build -t st-langflow-aio:latest . 2>&1 | tail -15

cd /home/docker/dockhand/stacks/Homelab/lang-flow
docker compose down
docker compose up -d

# Warten bis langflow antwortet
for i in $(seq 1 24); do
  sleep 5
  H="$(curl -s -m 3 http://localhost:7860/health || true)"
  [ -n "$H" ] && echo "alive after ${i}x5s: $H" && break
done
REMOTE
```

Falls der Build erneut abbricht oder seltsame Fehler zeigt, `--no-cache` benutzen:

```bash
docker build --no-cache -t st-langflow-aio:latest .
```

### 3. Verifikation in der laufenden Instanz

```bash
ssh root@pve-docker docker exec lang-flow-langflow-1 python3 -c '
from lfx.base.models.provider_registry import is_registered
from lfx.base.models.unified_models.provider_queries import get_model_providers, get_models_detailed
print("is_registered(MiniMax):", is_registered("MiniMax"))
print("MiniMax in providers:", "MiniMax" in get_model_providers())
mm = sorted(m.get("name") for g in get_models_detailed() for m in g if m.get("provider") == "MiniMax")
print("MiniMax catalog:", len(mm), "models:", mm)
'
ssh root@pve-docker docker exec lang-flow-langflow-1 sh -c '
echo "=== Binaries ==="
for b in ffmpeg chromium-browser node python3 yt-dlp; do
  p=$(command -v $b 2>/dev/null || echo MISSING)
  echo "  $b -> $p"
done
echo "=== Versions ==="
ffmpeg -version 2>&1 | head -1
chromium-browser --version 2>&1 | head -1
node --version
python3 --version
yt-dlp --version
'
```

Erwartetes Ergebnis:

- `is_registered(MiniMax): True`
- 8 MiniMax-Modelle im Catalog
- `ffmpeg version 8.1.2` (oder 7.x)
- `Chromium 153.0.…` (Fedora 46 Build)
- `node v22.23.1`

### 4. MiniMax-Smoke-Test (echter API-Hit)

```bash
ssh root@pve-docker docker exec lang-flow-langflow-1 python3 /tmp/smoke_test.py "dein_API_key_von_https://platform.minimax.io/"
```

### 5. Healthcheck im Compose (optional, klein)

Der jetzige Compose-`healthcheck` zeigt `Health=` nicht, weil er ohne Health-Block startet. Falls du eine formelle Probe willst, in `lang-flow/compose.yaml` unter `langflow:`:

```yaml
healthcheck:
  test: ["CMD", "curl", "-fsS", "http://localhost:7860/health"]
  interval: 30s
  timeout: 10s
  retries: 5
```

(curl liegt in Fedora-Images automatisch vor; bei zukünftigen Basis-Wechseln ggf. anpassen)

---

## Offene Punkte / Bekannte Probleme

1. **Server-Crash-Ursache unklar** — Logs nicht zugänglich. Bitte nach Wiederanlauf `/var/log/syslog` + `journalctl -u docker` checken, OOM war wahrscheinlich.

2. **Fedora 46 / setuptools<81 noch nicht live verifiziert** — wenns crasht, ist `/tmp/build.log` auf dem Server dein Freund. Typisch wäre, dass langflow selbst mit Python 3.15 nicht klar kommt (langflow PyPI-Metadaten stand auf Python <3.14 zur Zeit des Builds). Workaround-Fallback: auf Fedora 45 (Python 3.14) zurückgehen, Patch im Dockerfile HEAD schon vorbereitet — nur 46→45 tauschen.

3. **Pre-Release Versionssprünge** — wenn der User v0.4.0 final als Arbeitsversion will, sollte im Compose (und ggf. README) der Image-Tag auf `st-langflow-aio:v0.4.0` gepinnt werden statt `:latest`. Aktuell zeigt das Compose weiter auf `:latest`.

4. **chromium symlink auf `/usr/local/bin/chromium`** — wurde vorsorglich angelegt, falls anderes Tooling das kanonische `/usr/bin/chromium` erwartet. Fedora liefert aber offiziell nur `chromium-browser`. Wenn etwas die Symlink nicht mag, einfach wieder entfernen.

5. **`node` Version im Fedora-Image** — kommt mit node 22 statt der früheren 20. Falls yt-dlp-Wrapper (`yt-dlp-wrap`) das stört: im step 3 explizit nodejs20 pinnen. Aktuell kein Problem, aber Vorbehalt.

6. **Pre-pushed langflow releases** — v0.3.0 und v0.3.1 zeigen jeweils eigene Notes, die jetzt historisch mit dem Fedora-Switch teils widersprechen würden. Bei Bedarf `gh release edit v0.3.0/v0.3.1` aktualisieren oder beide zu `pre-release` markieren.

7. **`docs/INTEGRATION.md`** — ist die alte Doku der 5-File-Patch-Methode. Aktualisierung für Provider-Registry-Pfad steht aus, ist im aktuellen Diff nicht enthalten.

---

## Wichtige Dateien / Pfade

| Was | Wo |
|-----|-----|
| Repo-Root (lokal) | `/home/steimerbyte/st-langflow-aio` |
| Repo-Root (server) | `/home/docker/st-langflow-aio` |
| Compose-Stack | `/home/docker/dockhand/stacks/Homelab/lang-flow/compose.yaml` |
| Postgres-Host-Volume | `/home/docker/langflow/postgres/` |
| Flow-Host-Volume | `/home/docker/langflow/data/` |
| Dockerfile | `st-langflow-aio/Dockerfile` (neu, Fedora-basiert, ~117 Zeilen) |
| Auto-Register | `st-langflow-aio/inject/register_minimax.py` |
| Python-startup hook | `st-langflow-aio/inject/sitecustomize.py` |
| Verifikations-Script | `st-langflow-aio/inject/verify_inplace.py` (7 Checks) |
| Smoke-Test (echter API) | `st-langflow-aio/inject/smoke_test.py` |
| Standalone LCModelComponent | `st-langflow-aio/inject/lfx_components/lfx/components/minimax/minimax.py` |
| Backup alter Compose | `st-langflow-aio` selbst; Backup von `lang-flow/compose.yaml` als `compose.yaml.bak-20260924-0837` auf Server |

---

## Quick-Recovery-Block (Copy-Paste nach Server-Cycle)

```bash
ssh root@pve-docker 'bash -s' <<'REMOTE'
set -euo pipefail
cd /home/docker/st-langflow-aio
git fetch origin
git reset --hard origin/main
docker build -t st-langflow-aio:latest . 2>&1 | tail -10
cd /home/docker/dockhand/stacks/Homelab/lang-flow
docker compose down
docker compose up -d
for i in $(seq 1 24); do
  sleep 5
  H="$(curl -s -m 3 http://localhost:7860/health || true)"
  [ -n "$H" ] && echo "alive after ${i}x5s: $H" && break
done
docker exec lang-flow-langflow-1 python3 /tmp/verify_inplace.py
docker exec lang-flow-langflow-1 ffmpeg -version 2>&1 | head -1
docker exec lang-flow-langflow-1 chromium-browser --version 2>&1 | head -1
REMOTE
```
