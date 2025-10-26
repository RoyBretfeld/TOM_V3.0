# TOM v3.0 - Testing Policy Summary (No Mocks)

**Status:** ✅ Implementiert  
**Prinzip:** Real-Only, kein Mocking in Integration/E2E-Tests

---

## 🎯 Kernprinzipien

### ✅ Erlaubt
- **Unit-Tests**: Reine Logik (Parser, Math, FSM-Transitions)
- **Component-Tests**: Echte Subsysteme (WhisperX auf CUDA, Piper, Ollama)
- **Integration-Tests**: Echte Dienste (WS Gateway, ChromaDB, Redis)
- **E2E-Tests**: Echter SIP-Call via FreeSWITCH

### ❌ Verboten
- `unittest.mock` in Component/Integration/E2E
- `pytest-mock` in echten Tests
- Fake/Stub für TTS/ASR/LLM
- Media/WS Simulation
- Netzwerk-Simulation

---

## 📁 Implementierte Komponenten

### 1. Pytest-Konfiguration (`pytest.ini`)
- Marker: `unit`, `component`, `integration`, `e2e`, `slow`, `real_only`
- Timeout: 300s
- Asyncio-Mode: `auto`

### 2. Skip-Logik (`tests/conftest.py`)
- Verfügbarkeits-Checks: GPU, Ollama, Piper, FreeSWITCH, Redis, ChromaDB
- Fixtures: `ensure_real_env`, `cuda_available`, `ollama_client`, `freeswitch_available`
- Sauberes Skippen wenn Dependencies fehlen

### 3. Component-Tests (Real-Only)

**WhisperX GPU** (`tests/component/test_whisperx_gpu.py`):
- Echte Modell-Ladung auf CUDA
- Qualität-Tests der Transkription

**Piper TTS** (`tests/component/test_piper_tts.py`):
- Exe-Verfügbarkeit
- PCM16-Format-Verifikation
- Audio-Generierung

**Ollama LLM** (`tests/component/test_ollama_stream.py`):
- Token-Streaming-Tests
- Response-Latenz-Checks

### 4. Integration-Tests

**WS Gateway** (`tests/integration/test_gateway_roundtrip.py`):
- Echte WebSocket-Verbindung
- Roundtrip-Tests (Audio → Response)
- Barge-In Latenz-Tests (< 120ms)

### 5. Pre-Commit Hooks (`.pre-commit-config.yaml`)
- Verbot von Mock-Imports in Component/Integration/E2E
- Real-Only-Marker-Prüfung
- Pytest-Marker-Validierung
- Python Linting

---

## 🚀 Verwendung

### Test-Ebenen

```bash
# Unit-Tests (immer)
pytest tests/unit/ -v

# Component-Tests (GPU, Ollama, Piper erforderlich)
pytest tests/component/ -v

# Integration-Tests (Services erforderlich)
pytest tests/integration/ -v

# E2E-Tests (Full Stack)
pytest tests/e2e/ -v
```

### Verfügbarkeits-Checks

```bash
# GPU
nvidia-smi

# Ollama
curl http://localhost:11434/api/tags

# Piper
piper --version

# Redis
redis-cli ping

# FreeSWITCH
echo "status" | nc localhost 8021
```

### Skip-Status

```bash
# Skipped Tests anzeigen
pytest tests/component/ -v --tb=short -rs

# Ausgeben: "SKIPPED [1] ... Real-Only: Übersprungen, fehlt: GPU, OLLAMA"
```

---

## 📊 Test-Ebenen-Übersicht

| Ebene      | Marker        | Dependencies                    | Mocking erlaubt? |
|------------|---------------|----------------------------------|------------------|
| Unit       | `@pytest.mark.unit`       | Keine                           | Ja (nur Logik)  |
| Component  | `@pytest.mark.component`  | GPU, Ollama, Piper              | ❌ Nein         |
| Integration| `@pytest.mark.integration`| Services (WS, Redis, Prometheus)| ❌ Nein         |
| E2E        | `@pytest.mark.e2e`        | Full Stack + FreeSWITCH + SIP   | ❌ Nein         |

---

## 🔧 Troubleshooting

### Test wird geskippt

**Problem**: "Real-Only: Übersprungen, fehlt: GPU"

**Lösung**:
```bash
# Prüfe GPU-Verfügbarkeit
nvidia-smi

# Falls nicht installiert:
# Option 1: GPU installieren
# Option 2: Test auf maschinell mit GPU ausführen
# Option 3: Test für lokalen Rechner deaktivieren
```

### Mock-Import-Error

**Problem**: "Mock imports in echten Tests sind verboten!"

**Lösung**:
```python
# ❌ FALSCH (in component/integration/e2e):
from unittest import mock
@patch(...)  # NIEMALS!

# ✅ RICHTIG:
@pytest.mark.component
def test_real_component(ensure_real_env):
    # Echter Test ohne Mock
```

---

## 🎯 Definition of Done

✅ **Unit**: Reine Logik, 100% grün  
✅ **Component**: Echte ASR/TTS/LLM auf Zielhardware  
✅ **Integration**: Gateway + Services tauschen real Daten aus  
✅ **E2E**: Echter Anruf, hörbare Antwort, Latenz-KPIs unter Budget  
✅ **Keine Mocks**: Sauberes Skippen statt Faking  

---

## 📝 Nächste Schritte

1. **Component-Tests erweitern**: Weitere echte Hardware-Tests
2. **E2E-Tests**: FreeSWITCH Integration vollständig testen
3. **CI/CD**: Nightly Synthetic Calls validieren
4. **Monitoring**: Test-Metriken in Prometheus exportieren

---

**Testing Policy "No Mocks" erfolgreich implementiert!** ✅

