# 🎤 TOM v3.0 - Zwei Audio-Wege Definition

## 🎯 **Übersicht: Zwei parallele Audio-Pipelines**

Wir implementieren **zwei verschiedene Audio-Wege** für verschiedene Use Cases:

---

## 🚀 **Weg 1: WhisperX-Pipeline (High-Quality STT)**

### **Ziel:** 
Echte Spracherkennung mit GPU-Beschleunigung für **hochqualitative Transkription**

### **Architektur:**
```
Frontend → Audio-Chunks → Buffer → WAV-Datei → WhisperX (GPU) → Text → Ollama → Antwort
```

### **Komponenten:**
- **STT:** WhisperX `large-v2` (CUDA 12.1, RTX 4080)
- **LLM:** Ollama `qwen3:14b` (MoE-Architektur)
- **TTS:** Piper (lokale deutsche Stimme)
- **Audio-Format:** WAV-Dateien (16kHz, Mono, 16-bit)

### **Eigenschaften:**
- ✅ **Echte Spracherkennung** (keine Mock-Texte)
- ✅ **GPU-beschleunigt** (RTX 4080)
- ✅ **Hohe Qualität** (WhisperX large-v2)
- ✅ **Deutsche Sprache** (`language="de"`)
- ⏱️ **Latenz:** ~2-4 Sekunden (Batch-Verarbeitung)
- 📁 **Audio-Speicher:** Temporäre WAV-Dateien in `data/audio/`

### **Use Case:**
- **Qualitäts-fokussierte** Anwendungen
- **Offline-Verarbeitung** von Audio-Segmenten
- **Batch-Transkription** mit hoher Genauigkeit

---

## ⚡ **Weg 2: Realtime-Pipeline (Low-Latency)**

### **Ziel:** 
Echtzeit-Audio-Verarbeitung für **interaktive Gespräche** mit minimaler Latenz

### **Architektur:**
```
Frontend → Audio-Stream → VAD → Streaming-STT → Streaming-LLM → Streaming-TTS → Audio-Output
```

### **Komponenten:**
- **STT:** Streaming-fähige STT (z.B. Azure Speech, OpenAI Whisper API)
- **LLM:** Streaming LLM (Token-by-Token)
- **TTS:** Streaming TTS (Chunk-by-Chunk)
- **Audio-Format:** PCM-Stream (16kHz, Real-time)

### **Eigenschaften:**
- ⚡ **Ultra-low Latency** (<500ms)
- 🔄 **Echtzeit-Streaming** (keine Batch-Verarbeitung)
- 🎯 **Interaktiv** (natürliche Gespräche)
- 📡 **Cloud-basiert** (oder lokale Streaming-APIs)
- 💰 **Kosten-optimiert** (Pay-per-use)

### **Use Case:**
- **Live-Telefonie** (echte Gespräche)
- **Interaktive Assistenten**
- **Real-time Customer Service**

---

## 🔄 **Parallele Implementierung**

### **Server-Konfiguration:**
```python
# apps/realtime/config.py
class RealtimeConfig:
    # Weg 1: WhisperX (High-Quality)
    REALTIME_STT_WHISPERX = RealtimeMode.LOCAL
    WHISPERX_MODEL = "large-v2"
    WHISPERX_DEVICE = "cuda"
    
    # Weg 2: Realtime (Low-Latency)
    REALTIME_STT_STREAMING = RealtimeMode.PROVIDER
    STREAMING_PROVIDER = "azure"  # oder "openai"
    STREAMING_LATENCY_TARGET = 200  # ms
```

### **Frontend-Auswahl:**
```typescript
// web/dashboard/src/components/AudioModeSelector.tsx
interface AudioMode {
  mode: 'whisperx' | 'realtime';
  description: string;
  latency: string;
  quality: 'high' | 'ultra-low';
}
```

---

## 📊 **Vergleich der Wege**

| Eigenschaft | WhisperX-Pipeline | Realtime-Pipeline |
|-------------|-------------------|-------------------|
| **Latenz** | 2-4 Sekunden | <500ms |
| **Qualität** | Sehr hoch | Gut |
| **Kosten** | Lokal (GPU) | Cloud (Pay-per-use) |
| **Offline** | ✅ Ja | ❌ Nein |
| **Interaktiv** | ❌ Nein | ✅ Ja |
| **Use Case** | Batch-Verarbeitung | Live-Gespräche |

---

## 🎯 **Aktuelle Implementierung**

### **Status WhisperX-Pipeline:**
- ✅ **Server:** `fast_server.py` (Port 8081)
- ✅ **Audio-Bufferung:** WAV-Dateien in `data/audio/`
- ✅ **WhisperX:** CUDA 12.1, RTX 4080
- ✅ **Frontend:** `better.html` (Port 3003)
- 🔄 **In Arbeit:** PyTorch-CUDA Installation

### **Status Realtime-Pipeline:**
- 📋 **Geplant:** Streaming-STT Integration
- 📋 **Geplant:** Azure Speech Services
- 📋 **Geplant:** Ultra-low Latency Optimierung

---

## 🚀 **Nächste Schritte**

1. **WhisperX-Pipeline fertigstellen** (PyTorch-Installation)
2. **Realtime-Pipeline implementieren** (Azure/OpenAI Integration)
3. **Frontend-Modus-Auswahl** hinzufügen
4. **Performance-Messungen** durchführen
5. **A/B-Testing** zwischen beiden Wegen

---

**Ziel:** Beide Wege parallel verfügbar für verschiedene Anwendungsfälle! 🎤✨
