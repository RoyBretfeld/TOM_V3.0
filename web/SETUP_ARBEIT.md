# 🚀 TOM v3.0 - Setup Anleitung für Arbeit

## 📋 **Schnellstart Checkliste**

### ✅ **1. Projekt öffnen**
```bash
# Google Drive Ordner öffnen
cd "G:\Meine Ablage\_________FAMO\_____Tom-Telefonassistent_3-0"
```

### ✅ **2. Python Environment**
```bash
# Virtual Environment erstellen
python -m venv venv

# Aktivieren (Windows)
venv\Scripts\activate

# Dependencies installieren
pip install -r requirements.txt
```

### ✅ **3. Frontend Setup**
```bash
# In Dashboard Ordner wechseln
cd web\dashboard

# Node.js Dependencies installieren
npm install

# Development Server starten
npm run dev
```

### ✅ **4. Hybrid Realtime Server**
```bash
# Zurück zum Root
cd ..\..

# Hybrid Server starten
cd infra
python hybrid_server.py
```

---

## 🎯 **Was ist implementiert?**

### **Realtime API Pipeline:**
- **STT:** WhisperX mit GPU-Support (CUDA)
- **LLM:** Ollama mit Qwen3:14b MoE-Architektur
- **TTS:** Piper lokale deutsche Stimme
- **WebSocket:** Echtzeit-Kommunikation

### **Reinforcement Learning System:**
- **Feedback Collector:** SQLite-basierte Datensammlung
- **Reward Calculator:** Intelligente Belohnungsberechnung
- **Policy Bandit:** Thompson Sampling für Variantenauswahl
- **DeployGuard:** Sichere Deployment-Kontrolle

### **Frontend Dashboard:**
- **Mikrofon-Auswahl:** Automatische Geräteerkennung
- **Audio-Streaming:** WebSocket-basierte Kommunikation
- **Event-Log:** Live-Monitoring der Pipeline

---

## 🔧 **Konfiguration**

### **Environment Variables:**
```bash
# Hybrid Server Konfiguration
REALTIME_STT=local
REALTIME_LLM=local  
REALTIME_TTS=local

# Ollama Model
OLLAMA_MODEL=qwen3:14b

# Piper Voice
TTS_VOICE=de_DE-thorsten-medium
```

### **Ports:**
- **Frontend:** http://localhost:5173
- **Hybrid Server:** ws://localhost:8080

---

## 🧪 **Testing**

### **RL System Tests:**
```bash
# Alle Tests ausführen
pytest tests/

# Spezifische RL Tests
pytest tests/rl/
pytest tests/unit/test_deploy_guard.py
```

### **Realtime API Test:**
```bash
# Probe Script
python scripts/realtime_probe.py
```

---

## 📚 **Wichtige Dateien**

### **Core Components:**
- `apps/realtime/stt_whisperx.py` - WhisperX STT
- `apps/realtime/llm_ollama.py` - Ollama LLM
- `apps/realtime/tts_piper.py` - Piper TTS
- `infra/hybrid_server.py` - WebSocket Server

### **RL System:**
- `apps/rl/feedback.py` - Feedback Collection
- `apps/rl/policy_bandit.py` - Bandit Algorithm
- `apps/rl/deploy_guard.py` - Deployment Control

### **Frontend:**
- `web/dashboard/src/components/MicControls.tsx` - Mikrofon UI
- `web/dashboard/src/lib/ws.ts` - WebSocket Client

---

## 🚨 **Troubleshooting**

### **Port 8080 belegt:**
```bash
# Prozess finden
netstat -ano | findstr ":8080"

# Prozess beenden
taskkill /PID <PID> /F
```

### **Ollama nicht verfügbar:**
```bash
# Ollama starten
ollama serve

# Model prüfen
ollama list
```

### **Frontend Fehler:**
```bash
# Node modules neu installieren
rm -rf node_modules
npm install
```

---

## 🎯 **Nächste Schritte**

1. **Hybrid Server testen** - Echte WhisperX/Ollama/Piper Pipeline
2. **RL System aktivieren** - Feedback-Sammlung starten
3. **Performance optimieren** - GPU-Nutzung maximieren
4. **Deployment vorbereiten** - Produktions-Setup

---

## 📞 **Support**

Bei Problemen:
1. **Logs prüfen** - Console Output analysieren
2. **Tests laufen lassen** - `pytest tests/`
3. **Dokumentation lesen** - `docs/README_TOM_v3.0.md`

**Viel Erfolg! 🚀**
