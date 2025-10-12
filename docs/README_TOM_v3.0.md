# TOM v3.0 – Realtime-Telefonassistent

Ein modularer, hochperformanter Realtime-Telefonassistent mit niedriger Latenz und skalierbarer Architektur.

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

## 🚀 Schnellstart

```bash
# Repository klonen
git clone <repository-url>
cd TOM_V3.0

# Umgebung einrichten
cp infra/.env.example infra/.env
docker-compose -f infra/docker-compose.realtime.yml up -d

# Tests ausführen
python scripts/realtime_probe.py

# Dashboard starten
cd web/dashboard
npm install
npm run dev
```

## 📁 Projektstruktur

```
TOM_V3.0/
├── docs/                    # Dokumentation (schreibgeschützt)
│   ├── CBS-STARD.md        # CSB Prompt-Template
│   ├── Systemprompt Cursor-Start.md
│   ├── README_TOM_v3.0.md  # Diese Datei
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

## 🛡️ Sicherheit (CSB v1)

- **Read-Only Schutz**: `docs/` ist schreibgeschützt
- **UTF-8 Encoding**: Alle Ausgaben mit korrektem Encoding
- **Diff-Limits**: Max 30 Dateien oder 600 Zeilen pro Commit
- **SLOs**: Accuracy ≥ 95%, Mojibake = 0, Fail-Rate < 2%

## 🔄 Entwicklungsworkflow

1. **Prompt-Template**: Verwende `docs/CBS-STARD.md` für alle Cursor-Tasks
2. **Modulare Entwicklung**: Jede Komponente einzeln entwickeln und testen
3. **Realtime-Tests**: `scripts/realtime_probe.py` für Latenzmessungen
4. **CI/CD**: Automatische Tests und Qualitätsprüfungen

## 📊 Monitoring

- **Metriken**: Prometheus-Exporter in `apps/monitor/`
- **Health-Checks**: Automatische Überwachung aller Komponenten
- **Latenz-Monitoring**: Real-time Performance-Tracking
- **Dashboard**: Web-Interface für Live-Monitoring

## 🧪 Testing

- **Unit Tests**: `tests/unit/` für einzelne Module
- **E2E Tests**: `tests/e2e/` für komplette Anruf-Szenarien
- **Realtime Probes**: `scripts/realtime_probe.py` für Performance-Tests
- **Load Testing**: Skalierbarkeitstests für hohe Anrufvolumen

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
