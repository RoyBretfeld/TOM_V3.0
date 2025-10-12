# TOM v3.0 – Realtime-Telefonassistent

Ein modularer, hochperformanter Realtime-Telefonassistent mit niedriger Latenz und skalierbarer Architektur.

## 🚀 Schnellstart

```bash
# Repository klonen
git clone <repository-url>
cd TOM_V3.0

# Projekt initialisieren
python scripts/init_project.py

# Umgebung einrichten
cp infra/env.example infra/.env

# Docker-Services starten
docker-compose -f infra/docker-compose.realtime.yml up -d

# Dependencies installieren
pip install -r requirements.txt

# Tests ausführen
python -m pytest tests/

# Realtime-Probe
python scripts/realtime_probe.py
```

## 📁 Projektstruktur

```
TOM_V3.0/
├── docs/                    # Dokumentation (schreibgeschützt)
│   ├── CBS-STARD.md        # CSB Prompt-Template
│   ├── Systemprompt Cursor-Start.md
│   ├── README_TOM_v3.0.md  # Detaillierte Dokumentation
│   ├── SECURITY_GUARDRAILS_CURSOR.md
│   └── COMM_STAGE1_TOM_PROMPTS.md
├── apps/                    # Hauptanwendungen
│   ├── telephony_bridge/    # WebSocket-Bridge
│   ├── realtime/           # STT/LLM/TTS Streams
│   ├── dispatcher/         # FSM-basierte Steuerung
│   └── monitor/            # Metriken & Health
├── web/
│   └── dashboard/          # React Frontend
├── infra/                  # Container & Config
├── tests/                  # Test-Suite
│   ├── unit/              # Unit Tests
│   └── e2e/               # End-to-End Tests
├── scripts/               # Automatisierung
└── data/
    └── runtime/           # Flüchtige Laufzeitdaten
```

## 🏗️ Architektur-Übersicht

### Realtime-Pipeline
```
Telefonie → STT → LLM → TTS → Telefonie
    ↓         ↓      ↓      ↓
  Bridge   Stream  Stream  Stream
    ↓         ↓      ↓      ↓
  Redis ←→ Redis ←→ Redis ←→ Redis
```

### Kernkomponenten

- **Telephony Bridge** (`apps/telephony_bridge/`): WebSocket-Bridge zwischen Telefonie und Realtime-Pipeline
- **Realtime Engine** (`apps/realtime/`): STT/LLM/TTS Stream-Verarbeitung
- **Dispatcher** (`apps/dispatcher/`): FSM-basierte Anrufsteuerung
- **Monitor** (`apps/monitor/`): Metriken und Health-Checks
- **Web Dashboard** (`web/dashboard/`): React/Vite Frontend

## 🎯 Latenzziele

- **STT**: < 200ms (lokale Verarbeitung)
- **LLM**: < 500ms (Provider-abhängig)
- **TTS**: < 300ms (lokale Synthese)
- **Gesamtlatenz**: < 1000ms End-to-End

## 🔧 Technologie-Stack

- **Backend**: Python 3.11+ mit asyncio
- **Streaming**: WebSockets, Server-Sent Events
- **Message Queue**: Redis Streams
- **Frontend**: React 18 + Vite
- **Container**: Docker Compose
- **Monitoring**: Prometheus + Grafana

## 🛡️ CSB v1 - Cursor-Safety Baseline

Dieses Projekt folgt der CSB v1 (Cursor-Safety Baseline) für sichere Entwicklung:

- **UTF-8 Encoding**: Alle Schreiboperationen mit `encoding="utf-8"`
- **Read-Only Schutz**: `./docs/**` ist schreibgeschützt
- **Diff-Limits**: Max 30 Dateien oder 600 Zeilen pro Commit
- **SLOs**: Accuracy ≥ 95%, Mojibake = 0, Fail-Rate < 2%
- **Tests**: Mindestens 1 Test pro Änderung

## 🔧 Entwicklung

### Pre-commit Hooks
```bash
pre-commit run --all-files
```

### Tests ausführen
```bash
pytest
```

### CSB-Checks
```bash
python tools/ci_slo_check.py
```

### Realtime-Probe
```bash
python scripts/realtime_probe.py
```

## 📋 Akzeptanzkriterien

- [ ] Alle Tests bestehen (Unit + E2E)
- [ ] Latenzziele erreicht (< 1000ms End-to-End)
- [ ] CSB v1 Compliance eingehalten
- [ ] Docker-Container laufen stabil
- [ ] Dashboard zeigt Live-Metriken
- [ ] Realtime-Probes erfolgreich

## 🤝 Contributing

Bitte folge den CSB v1 Leitplanken und verwende das Prompt-Template aus `docs/CBS-STARD.md`.

## 📞 Support

Bei Fragen zur Architektur oder Entwicklung siehe `docs/COMM_STAGE1_TOM_PROMPTS.md` für detaillierte Cursor-Prompts.
