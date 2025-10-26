# Textfiles Collector Directory

Dieses Verzeichnis wird vom `host_inventory.py` befüllt und vom `node-exporter` via `--collector.textfile.directory` eingelesen.

## Verwendung

```bash
# Test-Run
python tools/host_inventory.py

# Inhalt prüfen
cat host_inventory.prom

# Node Exporter prüft dieses Verzeichnis alle 15 Sekunden
```

## Dateien

- `host_inventory.prom` - Hardware-Inventar in Prometheus-Format

## Metriken

Alle Metriken haben das Prefix `tom_`:
- `tom_host_cpu_info` - CPU-Modell und Kerne
- `tom_host_ram_bytes` - Gesamt-RAM
- `tom_gpu_count` - Anzahl GPUs
- `tom_gpu_vram_bytes` - VRAM pro GPU
- `tom_service_up` - Service-Status (Ollama, Piper, WhisperX, Chroma)
- `tom_readiness_realtime` - Realtime-Ready (≥12GB VRAM)
- `tom_readiness_single_agent` - Single-Agent-Ready (≥8GB VRAM)
- `tom_llm_info` - LLM-Modell-Name

