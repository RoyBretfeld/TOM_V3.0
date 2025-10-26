# TOM v3.0 – Realtime Loop Closure Telefonassistent

Ein hochmoderner, sicherer und performanter Realtime-Telefonassistent mit **vollständigem Loop Closure** von Mikrofoneingabe bis Audio-Ausgabe.

## 🏗️ Architektur-Übersicht

### Realtime Loop Closure Pipeline
```
Frontend → WebSocket → JWT-Auth → Rate-Limit → Mock-STT/LLM/TTS → Audio-Response → Frontend
    ↓           ↓           ↓            ↓              ↓              ↓           ↓
  React     Streaming   Security   Validation   Event-Driven   Mock-Flow   Audio-Playback
```

### Kernkomponenten

- **Frontend** (`web/dashboard/`): React/Vite UI mit Mikrofon-Streaming und Event-Log
- **Telephony Bridge** (`apps/telephony_bridge/`): WebSocket-Server mit Mock-Flow für Loop Closure
- **Realtime Adapter** (`apps/realtime/`): LLM/TTS-Streaming mit Feature-Flags
- **Monitor** (`apps/monitor/`): Prometheus-Metriken und Health-Checks
- **Nginx** (`infra/nginx.conf`): Load-Balancer mit Security-Hardening
- **Redis** (minimal): Nur für Auth-Cache und Replay-Schutz

## 🎯 Latenzziele (Loop Closure)

- **STT Mock**: < 100ms (simuliert)
- **LLM Mock**: < 200ms (Token-Streaming)
- **TTS Mock**: < 300ms (Audio-Frames)
- **WebSocket Roundtrip**: < 50ms
- **Gesamtlatenz**: **< 1500ms End-to-End** 🚀

## 🔧 Technologie-Stack

- **Frontend**: React 18 + Vite + TypeScript für moderne UI
- **Backend**: Python 3.11+ mit asyncio für WebSocket-Server
- **WebSocket**: `websockets` Library für bidirektionale Kommunikation
- **Authentifizierung**: JWT mit DEV-Bypass für Entwicklung
- **Audio-Processing**: Web Audio API mit Resampling (48kHz → 16kHz)
- **Mock-Flow**: Vollständige STT/LLM/TTS-Simulation für Loop Closure
- **Security**: **CSB v1 Compliance** mit vollständigem Security-Hardening
- **Container**: Docker Compose mit **Non-root, read-only** Sicherheit
- **Monitoring**: Prometheus-Metriken für Performance-Tracking

## 🚀 Schnellstart

```bash
# Repository klonen
git clone https://github.com/RoyBretfeld/TOM_V3.0.git
cd TOM_V3.0

# Backend starten
cp infra/env.example infra/.env
docker-compose -f infra/docker-compose.realtime.yml up -d

# Frontend starten
cd web/dashboard
npm install
npm run dev

# Health-Check
curl http://localhost:8080/healthz

# Tests ausführen
pytest tests/

# Loop Closure Probe
python scripts/realtime_probe.py
```

## 🎤 **Realtime Pipeline Status**

### ✅ **VOLLSTÄNDIG IMPLEMENTIERT** (16. Oktober 2025)

**Echte Realtime-Pipeline ohne Mocks - Produktionsbereit!**

- **Backend:** Secure WebSocket Gateway (Port 8081)
- **Provider:** OpenAI/Azure Realtime API Integration  
- **Frontend:** AudioWorklet-basierte Mikrofonkette
- **TTS:** Piper lokaler Echtbetrieb
- **FSM:** Zustandsmaschine ohne Mocks
- **Sicherheit:** JWT, Rate-Limits, CORS
- **Audio Recording:** DSGVO-konforme Aufzeichnung
- **Qualitätsprüfung:** Objektive Audio-Analyse

### 🔧 **Implementierte Komponenten:**
```
🎤 Mikrofon → 🌐 WebSocket → 🎯 STT → 🤖 LLM → 🔊 TTS → 🎵 Audio
```

### 📁 **Dateien:**
- **Backend:** `apps/telephony_bridge/ws_realtime.py`
- **Provider:** `apps/realtime/provider_realtime.py`
- **Frontend:** `web/dashboard/public/realtime.html`
- **TTS:** `apps/realtime/tts_piper_realtime.py`
- **FSM:** `apps/dispatcher/rt_fsm_realtime.py`
- **Tests:** `scripts/e2e_test_realtime.py`
- **Config:** `infra/env.realtime`

### 🚀 **Einfacher Test:**
1. **Server:** `python infra/simple_realtime_server.py`
2. **Frontend:** `web/simple_test.html`
3. **URL:** `ws://localhost:8081/`

### 🎤 **Audio Recording & Qualitätsprüfung:**

**DSGVO-konforme Aufzeichnung für interne Qualitätstests:**

1. **Recording aktivieren:**
   ```bash
   export RECORD_AUDIO=true
   export RECORD_PATH=./data/recordings
   export RECORD_RETENTION_HOURS=24
   ```

2. **Server starten:**
   ```bash
   python apps/telephony_bridge/ws_realtime.py
   ```

3. **Test durchführen:**
   ```bash
   python scripts/test_audio_recording.py
   ```

4. **Qualitätsprüfung:**
   ```bash
   python scripts/qc_audio.py data/recordings/test-call-001/test-call-001.wav
   ```

**Zielwerte:**
- RMS: 300-9000
- Clipping: < 0.001
- DC-Offset: < 200
- SNR: > 20 dB

---

1. **Browser öffnen**: `http://localhost:3000`
2. **Mikrofon auswählen**: Verfügbare Audio-Eingabegeräte
3. **JWT-Token eingeben**: `dev_token` (DEV-Modus)
4. **Verbinden**: WebSocket-Verbindung herstellen
5. **Streaming starten**: Audio-Chunks werden gesendet
6. **Events beobachten**: Live-Log aller eingehenden Nachrichten

### Erwartete Events:
- `connected` → Verbindung hergestellt
- `streaming_started` → Audio-Streaming aktiv
- `audio_chunk` → Audio-Daten gesendet
- `stt_final` → STT-Ergebnis erhalten
- `llm_token` → LLM-Tokens (streaming)
- `tts_audio` → TTS-Audio-Frames
- `turn_end` → Pipeline abgeschlossen
```

## 📁 Aktuelle Projektstruktur

```
TOM_V3.0/
├── web/dashboard/                 # React/Vite Frontend
│   ├── src/
│   │   ├── components/           # UI-Komponenten
│   │   ├── lib/                  # Audio-Utilities & WebSocket-Client
│   │   └── types/                # TypeScript-Definitionen
│   ├── package.json
│   └── vite.config.ts
├── apps/
│   ├── telephony_bridge/         # WebSocket-Server mit Mock-Flow
│   │   ├── ws.py                 # Hauptserver mit JWT-Auth
│   │   └── schemas.py            # Pydantic-Event-Validierung
│   ├── realtime/                 # Realtime-Adapter
│   │   ├── config.py             # Feature-Flags
│   │   ├── llm_stream.py         # LLM-Streaming (mock/provider)
│   │   ├── tts_stream.py         # TTS-Streaming (mock/Piper)
│   │   ├── stt_whisperx.py       # WhisperX STT-Integration
│   │   ├── llm_ollama.py         # Ollama LLM-Integration
│   │   └── tts_piper.py          # Piper TTS-Integration
│   ├── dispatcher/               # FSM-basierte Anrufsteuerung
│   │   ├── rt_fsm.py             # Realtime Finite State Machine
│   │   └── closing.py            # End-of-Call Feedback-Sammlung
│   ├── rl/                       # Reinforcement Learning System
│   │   ├── feedback.py           # Feedback Collector
│   │   ├── reward_calc.py        # Reward Calculator
│   │   ├── policy_bandit.py      # Thompson Sampling Bandit
│   │   ├── deploy_guard.py       # Shadow/A-B Deployment Guard
│   │   └── models.py             # Pydantic-Modelle
│   └── monitor/                  # Prometheus-Metriken
│       └── metrics.py            # RL-Metriken-Exporter
├── scripts/
│   └── realtime_probe.py         # Loop Closure Latenz-Messung
├── infra/
│   ├── docker-compose.realtime.yml
│   ├── env.example               # Erweiterte Konfiguration
│   └── nginx.conf
├── tests/
│   ├── unit/                     # Unit-Tests
│   ├── security/                 # Security-Tests
│   └── rl/                       # RL-System Tests
├── data/
│   ├── rl/                       # RL-Daten (SQLite, JSON-State)
│   └── audio/                    # Temporäre Audio-Dateien (WAV)
├── docs/
│   ├── README_TOM_v3.0.md        # Diese Datei
│   ├── ARCHITEKTUR.md            # Detaillierte Architektur
│   ├── RL_SYSTEM.md              # RL-System Dokumentation
│   ├── schemas/                  # JSON-Schemas
│   └── policies/                 # Policy-Varianten
└── notebooks/
    └── rl_offline_train.md       # Offline RL Training
```

## 🔄 Loop Closure Features

### Frontend (React/Vite)
- **Mikrofon-Auswahl**: Automatische Erkennung verfügbarer Audio-Geräte
- **Audio-Resampling**: 48kHz → 16kHz PCM16-Konvertierung
- **Live-Pegelanzeige**: Echtzeit-Visualisierung des Audio-Levels
- **WebSocket-Streaming**: Bidirektionale Kommunikation mit dem Backend
- **Event-Log**: Live-Anzeige aller eingehenden Events
- **JWT-Memory-State**: Sichere Token-Verwaltung ohne Persistierung

### Backend (Python/WebSocket)
- **Mock-Flow**: Vollständige STT/LLM/TTS-Simulation
- **Event-Validierung**: Pydantic-Schemas für alle WebSocket-Events
- **Rate-Limiting**: Token-Bucket-Algorithmus (120 msg/s)
- **DEV-Bypass**: JWT-Authentifizierung optional für Entwicklung
- **Strukturierte Logs**: Sicherheitskonformes Logging ohne sensible Daten

### Realtime-Adapter
- **Feature-Flags**: Dynamische Aktivierung von STT/LLM/TTS-Komponenten
- **LLM-Streaming**: Mock- und Provider-Modus für Language Models
- **TTS-Streaming**: Mock- und Piper-Modus für Text-to-Speech
- **Konfigurierbare Delays**: Anpassbare Mock-Latenzen für Tests

### Reinforcement Learning System
- **Feedback-Sammlung**: Automatische Bewertung am Gesprächsende
- **Policy-Bandit**: Thompson Sampling für optimale Policy-Auswahl
- **Reward-Berechnung**: Konfigurierbare Belohnungsformel
- **Shadow-Deployment**: Sichere A/B-Testing mit Traffic-Split
- **Offline-Training**: Wöchentliche Policy-Optimierung
- **Prometheus-Metriken**: Umfassendes RL-Monitoring

### Latenz-Messung
- **Realtime-Probe**: Automatisierte Messung der kompletten Pipeline
- **SLO-Verifikation**: Compliance-Checks für Latenz-Ziele
- **JSON-Export**: Strukturierte Ergebnisse für Analyse
- **WebSocket-Tests**: Ping/Pong und Audio-Chunk-Tests

## 🛡️ Sicherheit (CSB v1)

- **Read-Only Schutz**: `docs/` ist schreibgeschützt
- **UTF-8 Encoding**: Alle Ausgaben mit korrektem Encoding
- **Diff-Limits**: Max 30 Dateien oder 600 Zeilen pro Commit
- **SLOs**: Accuracy ≥ 95%, Mojibake = 0, Fail-Rate < 2%

## 🚀 Nächste Schritte

### Phase 1: Loop Closure (✅ Abgeschlossen)
- [x] Frontend mit Mikrofon-Streaming
- [x] WebSocket-Server mit Mock-Flow
- [x] Event-Validierung und Rate-Limiting
- [x] Realtime-Adapter mit Feature-Flags
- [x] Latenz-Messung und SLO-Verifikation

### Phase 2: Reinforcement Learning System (✅ Abgeschlossen)
- [x] Feedback Collector mit SQLite-Speicherung
- [x] Reward Calculator mit konfigurierbarer Formel
- [x] Policy Bandit mit Thompson Sampling
- [x] Policy Router Integration in FSM
- [x] End-of-Call Feedback-Sammlung
- [x] Prometheus-Metriken für RL-System
- [x] Deploy Guard für Shadow/A-B Testing
- [x] Offline Training Notebook

### Phase 3: Echte Provider-Integration
- [ ] OpenAI API-Integration für LLM
- [ ] Whisper-Integration für STT
- [ ] Piper-Integration für TTS
- [ ] Provider-spezifische Konfiguration

### Phase 4: Produktions-Features
- [ ] Telefonie-Bridge für echte Anrufe
- [ ] Monitoring und Alerting
- [ ] Load-Balancing und Skalierung
- [ ] Security-Hardening für Produktion

## 📞 Support

Bei Fragen oder Problemen:
1. **Dokumentation**: `docs/ARCHITEKTUR.md` für Details
2. **Tests**: `pytest tests/` für Funktionsprüfung
3. **Probe**: `python scripts/realtime_probe.py` für Latenz-Tests
4. **Logs**: Docker-Logs für Debugging

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
