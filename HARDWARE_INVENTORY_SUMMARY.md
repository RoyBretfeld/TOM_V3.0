# TOM v3.0 - Hardware Inventory & Readiness System

**Status:** ✅ Implementiert  
**Zweck:** Automatische Hardware-Erkennung und Readiness-Gates für Prometheus/Grafana

---

## 🎯 Was wird implementiert

### 1. Host Inventory Exporter (`tools/host_inventory.py`)
- **CPU-Info**: Modell, Anzahl Kerne
- **RAM**: Gesamtmenge in Bytes
- **GPU**: Anzahl, VRAM pro Karte, Name, Treiber, CUDA-Version
- **Services**: Ollama, ChromaDB, Piper, WhisperX (Up/Down)
- **LLM-Modell**: Aktuelles Ollama-Modell
- **Readiness-Gates**: Realtime vs. Single-Agent

### 2. Readiness-Logik

**Realtime-Ready** (für vollständige Pipeline):
- ≥ 12 GB VRAM (z.B. RTX 4070 Ti/SUPER, RTX 4080)
- ≥ 32 GB RAM
- Services: Ollama, WhisperX, Piper, ChromaDB (alle UP)

**Single-Agent-Ready** (Notbetrieb):
- ≥ 8 GB VRAM (z.B. RTX 3070 Ti)
- ≥ 16 GB RAM
- Services: Ollama, Piper (mindestens)

### 3. Systemd Timer (`infra/systemd/host-inventory.{service,timer}`)
- Aktualisiert alle 30 Sekunden
- Schreibt in `/var/lib/node_exporter/textfile_collector/host_inventory.prom`
- Linux-only (Windows: Task Scheduler + `HOST_INVENTORY_OUT` ENV)

### 4. Grafana Dashboard (`infra/grafana/dashboards/host_inventory.json`)
- **Realtime Ready** (grün/rot)
- **Single-Agent Ready** (grün/rot)
- GPU-Inventar-Tabelle
- Services-Status-Tabelle
- CPU/RAM/LLM-Info
- GPU Utilization & VRAM (via DCGM)

---

## 🚀 Verwendung

### 1. Linux Setup

```bash
# Host Inventory Script ausführbar machen
chmod +x tools/host_inventory.py

# Textfile-Verzeichnis erstellen
sudo mkdir -p /var/lib/node_exporter/textfile_collector
sudo chown nodeexp:nodeexp /var/lib/node_exporter/textfile_collector

# Test-Run
HOST_INVENTORY_OUT=/var/lib/node_exporter/textfile_collector/host_inventory.prom \
  python3 tools/host_inventory.py

# Inhalt prüfen
cat /var/lib/node_exporter/textfile_collector/host_inventory.prom
```

### 2. Systemd Service & Timer

```bash
# Services kopieren
sudo cp infra/systemd/host-inventory.service /etc/systemd/system/
sudo cp infra/systemd/host-inventory.timer /etc/systemd/system/

# Timer aktivieren
sudo systemctl enable host-inventory.timer
sudo systemctl start host-inventory.timer

# Status prüfen
systemctl status host-inventory.timer
journalctl -u host-inventory.service -f
```

### 3. Docker Compose Starten

```bash
# Monitoring-Stack mit Textfile-Collector starten
docker-compose -f infra/docker-compose.monitoring.yml up -d

# Inhalt in Container prüfen
docker exec tom-node-exporter cat /textfiles/host_inventory.prom
```

### 4. Grafana Dashboard Importieren

```bash
# Dashboard-Import
# Grafana UI: Dashboards → Import
# Datei: infra/grafana/dashboards/host_inventory.json
```

---

## 📊 Metriken (Prometheus)

### Host-Info
```
tom_host_cpu_info{model="AMD Ryzen 9 5950X",cores="16"} 1
tom_host_ram_bytes 68719476736
```

### GPU-Info
```
tom_gpu_count 1
tom_gpu_driver_info{driver="535.54.03",cuda="12.3"} 1
tom_gpu_vram_bytes{index="0",name="NVIDIA GeForce RTX 4080"} 17179869184
```

### Services
```
tom_service_up{name="ollama"} 1
tom_service_up{name="whisperx"} 1
tom_service_up{name="piper"} 1
tom_service_up{name="chroma"} 1
```

### Readiness-Gates
```
tom_readiness_realtime 1
tom_readiness_single_agent 1
```

### LLM-Info
```
tom_llm_info{name="qwen3:14b"} 1
```

---

## 🔧 Troubleshooting

### Problem: Metriken werden nicht angezeigt

**Lösung**:
```bash
# Prüfe ob Textfile erstellt wurde
ls -lh /var/lib/node_exporter/textfile_collector/

# Prüfe Inhalt
cat /var/lib/node_exporter/textfile_collector/host_inventory.prom

# Prüfe Node Exporter
curl http://localhost:9100/metrics | grep tom_
```

### Problem: Readiness immer 0

**Lösung**:
- **VRAM**: `nvidia-smi` → Prüfe Total Memory
- **RAM**: `free -h` → Prüfe MemTotal
- **Services**: Grafana Dashboard → Services-Status prüfen

### Problem: Windows Setup

**Lösung**:
```powershell
# Task Scheduler (Admin)
# Aktion: python.exe C:\tom\tools\host_inventory.py
# ENV: HOST_INVENTORY_OUT=C:\Program Files\windows_exporter\textfile_inputs\host_inventory.prom
# Trigger: Alle 30 Sekunden
```

---

## 🎯 Definition of Done

✅ **Host-Info**: CPU, RAM, GPU erkannt  
✅ **GPU-Info**: VRAM, Name, Treiber, CUDA  
✅ **Services**: Ollama, WhisperX, Piper, ChromaDB Status  
✅ **Readiness-Gates**: Realtime vs. Single-Agent berechnet  
✅ **Grafana Dashboard**: Metriken sichtbar  
✅ **Auto-Update**: Alle 30 Sekunden  

---

## 📝 Nächste Schritte

1. **Grafana Alerts**: Auf `tom_readiness_realtime == 0` > 5 min
2. **Mehrere GPUs**: Erweiterte GPU-Panels für Index 1, 2, ...
3. **Chroma-DB-Info**: DB-Size, Embeddings-Count (optional)
4. **Windows-Exporter**: Vollständige Windows-Unterstützung

---

**Hardware Inventory & Readiness System erfolgreich implementiert!** ✅

