# st-langflow-aio

<p align="center">
  <img src="docs/images/header.png" alt="st-langflow-aio header" />
</p>

<p align="center">
  <img src="docs/images/second.png" alt="MiniMax Provider in Langflow" />
</p>

**Langflow + MiniMax als voll integrierter Global Model Provider.**

> v0.3.0 — Registry-basiert, kompatibel mit Langflow `latest` (1.13+), Open Source, kein API-Key noetig fuer das Image selbst.

## Was es macht

- MiniMax erscheint in **Settings → Model Providers** und im **Agent "Model Provider" Dropdown** — wie OpenAI, Anthropic, Ollama
- 8 MiniMax-Modelle (M3, M2.7, M2.7-highspeed, M2.5, M2.5-highspeed, M2.1, M2.1-highspeed, M2) auswaehlbar
- Tool Calling, Vision, Video, Thinking (M3) alle unterstuetzt
- Langflow + ffmpeg + Chromium (puppeteer) + Node.js 20 + yt-dlp vorinstalliert

## Quickstart

```bash
git clone https://github.com/steimerbyte/st-langflow-aio.git
cd st-langflow-aio

# .env anlegen
cat > .env << 'EOF'
LANGFLOW_SECRET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
LANGFLOW_SUPERUSER=admin@example.com
LANGFLOW_SUPERUSER_PASSWORD=changeme
MINIMAX_API_KEY=sk-cp-your-key-here
EOF

# Bauen und starten
docker build --no-cache -t st-langflow-aio .
docker compose up -d
```

Browser → http://localhost:7860

- **Settings → Model Providers → MiniMax** → API-Key eintragen → Save
- Neuer Flow → **Agent** → Model Provider: **MiniMax** → Model: **MiniMax-M3**

## Setup ohne MiniMax

Das Image laeuft auch ohne MiniMax-Key. Setze einfach `MINIMAX_API_KEY=` (leer) oder lass die Zeile weg — die anderen Tools (Langflow, ffmpeg, Chromium, yt-dlp) funktionieren unabhaengig.

## Verifizieren

```bash
# Provider-Registrierung verifizieren (Registry-State, 7 Checks)
docker exec -it $(docker ps -qf name=langflow) python3 /tmp/verify_inplace.py

# Echter API-Test mit deinem Key
docker exec -it $(docker ps -qf name=langflow) python3 /tmp/smoke_test.py sk-cp-your-key
```

## Unterstuetzte Modelle

| Model | Context | Features |
|-------|---------|----------|
| MiniMax-M3 | 1M | Bild, Video, Thinking |
| MiniMax-M2.7 | 200k | highspeed ~100 tps |
| MiniMax-M2.5 | 200k | highspeed ~100 tps |
| MiniMax-M2.1 | 200k | highspeed ~100 tps |
| MiniMax-M2 | 200k | Agentic, Reasoning |

API-Key holen: https://platform.minimax.io/

## Troubleshooting

| Problem | Loesung |
|---------|--------|
| MiniMax nicht in Settings sichtbar | `docker compose down -v && docker compose up -d` |
| `invalid x-api-key` Fehler | Key im [MiniMax Console](https://platform.minimax.io/) pruefen, kein Whitespace |
| Provider im Agent nicht waehlbar | Browser Hard-Refresh (Strg+Shift+R) |
| Alte Build-Caches aktiv (Pre-v0.3 Patch-Ansatz) | `docker compose down -v && docker rmi st-langflow-aio -f && docker build --no-cache .` |
| `MiniMax is_registered() returned False` nach Container-Start | `docker exec -it <container> python3 /tmp/verify_inplace.py` — Auto-Register über `sitecustomize.py` greift erst beim nächsten Prozess-Start, dann `docker compose restart langflow` |

## Architektur

Seit v0.3.0 nutzt die Integration **`provider_registry.register_provider()`** statt
Datei-Patching. Das macht das Image upgrade-tolerant gegenüber Langflow-Refactors.

| Komponente | Zweck |
|------------|-------|
| `inject/register_minimax.py` | ProviderDescriptor + catalog_loader (8 Modelle) |
| `inject/sitecustomize.py` | Auto-Registrierung beim Python-Startup |
| `inject/verify_inplace.py` | Verifiziert Registry-State (7 Checks) |
| `inject/smoke_test.py` | Echter API-Smoke-Test gegen MiniMax |
| `inject/lfx_components/.../minimax.py` | Standalone `MiniMaxModelComponent` (Custom-Component-Pfad, optional) |

**Was passiert beim Build:** `register_minimax.py` und `sitecustomize.py` werden
in `<site-packages>/` installiert. Beim Start eines jeden Python-Prozesses
führt Python `sitecustomize.py` automatisch aus, welches die Registrierung in
`lfx.base.models.provider_registry` vornimmt — **kein Patch der Core-Files**.

Vorteile gegenüber dem alten Patching-Ansatz:
- Funktioniert mit jeder künftigen `langflowai/langflow:latest`-Version
- Eine Quelle der Wahrheit für MiniMax-Metadaten
- Kein Cascade-Replace von Strings, das bei Refactors bricht

Details: [docs/INTEGRATION.md](docs/INTEGRATION.md)

## Struktur

```
st-langflow-aio/
├── Dockerfile                    # Build mit Registry-Install
├── docker-compose.yml            # Postgres + Langflow
├── inject/
│   ├── register_minimax.py      # ProviderRegistry-Deskriptor
│   ├── sitecustomize.py         # Auto-Registrierung beim Startup
│   ├── verify_inplace.py        # Verifiziert Registrierung (7 Checks)
│   └── smoke_test.py            # API-Smoke-Test
└── docs/INTEGRATION.md          # Tech-Doku
```

## Releases

- [v0.3.0](https://github.com/steimerbyte/st-langflow-aio/releases/tag/v0.3.0) — aktuell, Registry-basiert, kompatibel mit Langflow 1.13+
- [v0.2.x](https://github.com/steimerbyte/st-langflow-aio/releases/tag/v0.2.3) — Patching-basiert (Legacy)
- v0.1.x — Pre-release Iterationen

## Lizenz & Credits

MiniMax nutzt das offizielle Anthropic SDK gegen den MiniMax Anthropic-kompatiblen Endpunkt — kein separates MiniMax SDK noetig.

API-Docs: https://platform.minimax.io/docs/api-reference/text-anthropic-api

---

## Hinweis zur KI-Unterstuetzung

Bei der Entwicklung dieses Projekts wurden teilweise oder vollstaendig KI-gestuetzte Tools und Technologien eingesetzt.
