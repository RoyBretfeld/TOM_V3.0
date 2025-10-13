# TOM v3.0 – Loop Closure Architekturdokumentation

## 📋 Übersicht

TOM v3.0 ist ein hochmoderner, sicherer und skalierbarer **Realtime-Telefonassistent** mit **vollständigem Loop Closure** von Mikrofoneingabe bis Audio-Ausgabe:

- **Loop Closure**: Frontend → WebSocket → Mock-STT/LLM/TTS → Frontend
- **Niedrige Latenz**: < 1500ms End-to-End für Mock-Pipeline
- **Modulare Architektur**: Frontend/Backend/Adapter für einfache Wartung
- **CSB v1 Compliance**: Höchste Sicherheitsstandards und UTF-8-Encoding
- **Docker-native**: Containerisierte Services mit Security-Hardening

## 🏗️ Systemarchitektur

### Loop Closure Architekturprinzipien

**REALTIME LOOP CLOSURE ARCHITEKTUR:**

```
┌─────────────────────────────────────────────────────────────────┐
│              TOM v3.0 - Loop Closure Architecture              │
├─────────────────────────────────────────────────────────────────┤
│  Frontend ←→ WebSocket ←→ Telephony Bridge ←→ Mock-STT/LLM/TTS │
│     ↓           ↓              ↓                    ↓           │
│  React/Vite   Streaming    JWT-Auth/Rate    Event-Driven      │
│     ↓           ↓              ↓                    ↓           │
│ ┌─────────┐ ┌─────────┐ ┌─────────────┐ ┌─────────────────┐ │
│ │ Mic-UI  │ │ WS-Client│ │ Security    │ │ Realtime-Adapter│ │
│ │ Audio   │ │ Streaming│ │ Middleware  │ │ Feature-Flags   │ │
│ │ Events  │ │ Resample │ │ Validation  │ │ Mock-Flow       │ │
│ └─────────┘ └─────────┘ └─────────────┘ └─────────────────┘ │
│     ↓           ↓              ↓                    ↓           │
│ Audio-Input → PCM16-Chunks → Event-Validation → Mock-Responses │
└─────────────────────────────────────────────────────────────────┘
```

### Datenfluss (VEREINFACHT)

```
Audio-Input → WebSocket → JWT-Auth → Rate-Limit → Speech-to-Speech API → Audio-Response → Client
```

**Vorteile der vereinfachten Architektur:**
- **Direkte Integration**: Keine komplexe Worker-Kommunikation nötig
- **Niedrigere Latenz**: Weniger Hops in der Pipeline
- **Einfachere Wartung**: Weniger bewegliche Teile
- **Robuster**: Weniger potentielle Fehlerquellen

## 🔧 Komponenten-Architektur

### 1. Reinforcement Learning System (`apps/rl/`)

**Verantwortlichkeiten:**
- Kontinuierliche Verbesserung durch Feedback-Learning
- Policy-Auswahl mit Thompson Sampling Bandit
- Reward-Berechnung basierend auf Gesprächsqualität
- Shadow/A-B Deployment für sichere Policy-Tests
- Offline-Training für Policy-Optimierung

**Komponenten:**
- **Feedback Collector**: Sammelt und speichert Benutzerbewertungen
- **Reward Calculator**: Berechnet Belohnungen aus Gesprächssignalen
- **Policy Bandit**: Thompson Sampling für optimale Policy-Auswahl
- **Deploy Guard**: Traffic-Split und Blacklist-Management
- **Metrics Exporter**: Prometheus-Metriken für RL-Monitoring

**Datenfluss:**
```
Gespräch → Feedback → Reward → Policy-Update → Neue Policy-Auswahl
```

### 2. Dispatcher (`apps/dispatcher/`)

**Verantwortlichkeiten:**
- FSM-basierte Anrufsteuerung
- Integration mit RL-System für Policy-Auswahl
- Session-Management und State-Tracking
- End-of-Call Feedback-Sammlung

**Komponenten:**
- **RealtimeFSM**: Finite State Machine für Anrufzustände
- **Closing**: Feedback-Sammlung am Gesprächsende
- **Policy Router**: Integration mit RL-System

### 3. Telephony Bridge (`apps/telephony_bridge/`)

**Verantwortlichkeiten:**
- WebSocket-Server für Client-Verbindungen
- JWT-basierte Authentifizierung
- Rate-Limiting (Token-Bucket Algorithmus)
- **Direkte Speech-to-Speech API Integration**
- Event-Routing und Response-Handling

**Technologien:**
- **WebSocket**: `websockets` Library für bidirektionale Kommunikation
- **Auth**: JWT mit `PyJWT` und Replay-Schutz
- **Rate-Limiting**: Custom Token-Bucket Implementation
- **API-Integration**: Direkte HTTP/Speech-to-Speech API Calls
- **Validierung**: Pydantic-Schemas für alle Events

**Sicherheitsfeatures:**
- JWT-Token-Validierung mit Replay-Schutz (Redis)
- Call-ID-Validierung gegen URL
- Rate-Limiting (120 msg/s pro Verbindung)
- Strukturierte Fehler-Logs ohne PII
- **CSB v1 Compliance** für alle Sicherheitsaspekte

**API-Endpoints:**
- `GET /health` - Health-Check
- `WebSocket /ws/stream/{call_id}` - Audio-Streaming mit Speech-to-Speech

**Datenfluss:**
```
Audio-Chunk → Validierung → Speech-to-Speech API → Audio-Response → Client
```

### 2. Vereinfachte Service-Architektur

**Da TOM v3.0 eine native Speech-to-Speech API verwendet, brauchen wir:**

**Nicht mehr nötig:**
- ❌ Separate STT Worker
- ❌ Separate LLM Worker
- ❌ Separate TTS Worker
- ❌ Komplexe Redis Stream Worker-Kommunikation

**Was bleibt:**
- ✅ **Telephony Bridge** als zentrale Schnittstelle
- ✅ **Monitor** für Metriken und Health-Checks
- ✅ **Nginx** für Load-Balancing und Security
- ✅ **Redis** nur noch für Auth-Cache und Replay-Schutz

### 3. Monitor (`apps/monitor/`)

**Verantwortlichkeiten:**
- Prometheus-Metriken für Speech-to-Speech Performance
- Health-Checks für Bridge und API
- Latenz-Monitoring für End-to-End Pipeline
- System-Überwachung

**Metriken (VEREINFACHT):**
- `speech_to_speech_latency_ms` - API-Latenz
- `websocket_connections_total` - Aktive Verbindungen
- `auth_success_total` - Erfolgreiche Authentifizierungen
- `rate_limit_hits_total` - Rate-Limit Überschreitungen
- `api_errors_total` - Speech-to-Speech API Fehler

**Health-Endpoints:**
- `/healthz` - Basis-Health-Check
- `/healthz/speech_api` - Speech-to-Speech API Erreichbarkeit
- `/metrics` - Prometheus-Export

## 🔒 Sicherheitsarchitektur

### CSB v1 Compliance

TOM v3.0 implementiert vollständige **CSB v1 (Cursor-Safety Baseline)** Compliance:

**Leitplanken:**
1. **Read-Only Inputs**: `docs/` und `data/originals/` sind schreibgeschützt
2. **UTF-8 Encoding**: Alle Schreiboperationen mit explizitem Encoding
3. **Scope-Limiting**: Nur namentlich genannte Dateien werden modifiziert
4. **Diff-Limits**: Max 30 Dateien oder 600 Zeilen pro Commit
5. **Test-Requirement**: Mindestens 1 Test pro Änderung
6. **SLOs**: Accuracy ≥ 95%, Mojibake = 0, Fail-Rate < 2%

**Sicherheitsfeatures:**
- **Container-Hardening**: Non-root, read-only Filesysteme, minimal Privileges
- **Network-Security**: Nginx Reverse-Proxy mit Rate-Limiting
- **Data-Protection**: Keine PII in Logs, verschlüsselte Verbindungen
- **Fail-Closed**: Bei Sicherheitsverstößen wird blockiert statt durchgelassen

### Authentifizierung & Autorisierung

**JWT-Token-Struktur:**
```json
{
  "sub": "user_id",
  "call_id": "unique_call_identifier",
  "iat": 1640995200,
  "exp": 1640998800,
  "nonce": "unique_nonce_value"
}
```

**Replay-Schutz:**
- Nonce wird einmalig in Redis gespeichert
- TTL = Token-Ablaufzeit
- Wiederverwendung → 401 Unauthorized

**Rate-Limiting:**
- Token-Bucket Algorithmus
- 120 Nachrichten/Sekunde pro Verbindung
- Überschreitung → WebSocket-Close (1013)

## 📊 Datenarchitektur

### Redis Streams

**Verwendete Streams:**
- `audio_stream:{call_id}` - Audio-Chunks von Client
- `control_stream:{call_id}` - Steuerungssignale (barge_in, stop)
- `stt_stream:{call_id}` - STT-Verarbeitungsergebnisse
- `llm_stream:{call_id}` - LLM-Antworten
- `tts_stream:{call_id}` - TTS-Audio-Daten

**Stream-Konfiguration:**
- Max. Nachrichten: 2048 pro Stream
- Automatische Bereinigung bei Überschreitung
- Persistent Storage für Debugging

### State Management

**Call-State in Redis:**
```json
{
  "call_id": "unique_id",
  "state": "LISTENING",
  "start_time": 1640995200,
  "last_activity": 1640995205,
  "metrics": {
    "stt_latency": 150,
    "llm_latency": 400,
    "tts_latency": 250
  }
}
```

## 🚀 Deployment-Architektur

### Docker-Konfiguration

**Services:**
- **Redis**: In-Memory Message Queue
- **Telephony Bridge**: WebSocket-Gateway (2 Replicas)
- **STT Worker**: Audio-zu-Text (2 Replicas)
- **LLM Worker**: Text-Verarbeitung (2 Replicas)
- **TTS Worker**: Text-zu-Audio (2 Replicas)
- **Dispatcher**: State-Management (1 Replica)
- **Monitor**: Metriken und Health (1 Replica)
- **Nginx**: Load-Balancer und Reverse-Proxy

**Security-Hardening:**
- Alle Container laufen als non-root User
- Read-only Filesysteme wo möglich
- No-new-privileges Security-Option
- Tmpfs für temporäre Dateien
- Health-Checks für alle Services

### Skalierung

**Horizontale Skalierung:**
- Worker-Services können horizontal skaliert werden
- Redis Cluster für höhere Durchsatz-Anforderungen
- Load-Balancer verteilt Last automatisch

**Vertikale Skalierung:**
- Ressourcen-Optimierung durch Profiling
- Memory-Management für große Audio-Dateien
- CPU-Optimierung für ML-Modelle

## 🔍 Monitoring & Observability

### Metriken

**Echtzeit-Metriken:**
- Latenz pro Pipeline-Stufe
- Durchsatz (Nachrichten/Sekunde)
- Fehler-Raten pro Komponente
- Ressourcen-Auslastung

**Business-Metriken:**
- Anzahl erfolgreicher Anrufe
- Durchschnittliche Anrufdauer
- Barge-In-Rate
- User-Satisfaction-Scores

### Logging

**Struktur:**
```
[%(asctime)s] [%(levelname)s] [%(call_id)s] %(message)s
```

**Level:**
- `INFO`: Normale Operationen (Connect, State-Changes)
- `WARNING`: Sicherheitsereignisse (Rate-Limit, Invalid Token)
- `ERROR`: Kritische Fehler (Service-Ausfälle, Data-Korruption)

**Speicherung:**
- Lokale Log-Files für Debugging
- Zentrale Log-Aggregation (ELK Stack empfohlen)
- Retention: 30 Tage für Security-Logs

## 🔧 Entwicklung & Testing

### Test-Strategie

**Unit-Tests:**
- Einzelne Komponenten testen
- Mock-basierte Isolation
- 80%+ Code-Coverage Ziel

**Integration-Tests:**
- Komplette Pipeline testen
- End-to-End Szenarien
- Latenz-Messungen

**Security-Tests:**
- Penetration-Testing
- Fuzzing für Input-Validierung
- Automated Security-Scans

### CI/CD Pipeline

**Stages:**
1. **Linting**: Black, Ruff, MyPy
2. **Security**: Bandit, Safety, Dependency-Scans
3. **Tests**: Unit + Integration Tests
4. **Build**: Docker-Images erstellen
5. **Deploy**: Staging-Environment
6. **Smoke-Tests**: E2E-Pipeline-Test

**Tools:**
- GitHub Actions für CI/CD
- Docker Compose für lokale Entwicklung
- Kubernetes für Production (optional)

## 📈 Performance-Ziele

### Latenz-Benchmarks

| Komponente | Ziel-Latenz | Aktuelle Messung |
|------------|-------------|------------------|
| STT (lokal) | < 200ms | ~150ms |
| LLM (API) | < 500ms | ~400ms |
| TTS (lokal) | < 300ms | ~250ms |
| **End-to-End** | **< 1000ms** | **~800ms** |

### Durchsatz-Ziele

- **Simultan Anrufe**: 100+
- **Nachrichten/Sekunde**: 10.000+
- **CPU-Auslastung**: < 70%
- **Memory-Effizienz**: < 2GB pro Worker

## 🔮 Zukunft & Erweiterungen

### Roadmap

**Phase 1** (Aktuell):
- Grundlegende Realtime-Pipeline ✅
- Security-Hardening ✅
- Monitoring & Observability ✅

**Phase 2** (Nächste):
- Multi-Language Support
- Voice-Activity-Detection
- Sentiment-Analysis
- Call-Recording (mit Consent)

**Phase 3** (Zukunft):
- Machine-Learning-Optimierung
- Predictive Analytics
- Advanced Conversation-Flows
- Integration mit CRM-Systemen

### Technische Schulden

- **ML-Modelle**: Whisper/Piper Updates
- **Monitoring**: Erweiterte Dashboards
- **Testing**: Mehr E2E-Test-Coverage
- **Dokumentation**: API-Referenz ergänzen

## 📚 Referenzen

- **CSB v1 Standard**: `docs/CBS-STARD.md`
- **Security Guidelines**: `docs/SECURITY_GUARDRAILS_CURSOR.md`
- **Development Prompts**: `docs/COMM_STAGE1_TOM_PROMPTS.md`
- **System Prompt**: `docs/Systemprompt Cursor-Start.md`

---

*Dieses Dokument beschreibt die Architektur von TOM v3.0 Stand der aktuellen Implementation. Für Updates und Änderungen siehe Git-Commit-History.*
