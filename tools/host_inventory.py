#!/usr/bin/env python3
"""
TOM v3.0 - Host Inventory Exporter (Real-Only)
Sammelt Hardware-Infos und Service-Status für Prometheus
"""

import os
import sys
import subprocess
import json
import shutil
import socket
import time
import platform
import re
import urllib.request
from pathlib import Path


# Konfiguration
OUT = os.getenv("HOST_INVENTORY_OUT", "/var/lib/node_exporter/textfile_collector/host_inventory.prom")
OLLAMA = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
CHROMA = os.getenv("CHROMA_URL", "http://127.0.0.1:8000")
PIPER_BIN = os.getenv("PIPER_BIN", shutil.which("piper") or "piper")
PHONE_SALT = os.getenv("PHONE_HASH_SALT", "not-set")


def run(cmd, timeout=3):
    """Führt Shell-Kommando aus"""
    try:
        return subprocess.check_output(
            cmd, 
            stderr=subprocess.DEVNULL, 
            timeout=timeout, 
            shell=isinstance(cmd, str)
        ).decode().strip()
    except Exception:
        return ""


def nvidia_smi_q(query):
    """Fragt nvidia-smi ab"""
    smi = shutil.which("nvidia-smi")
    if not smi:
        return ""
    return run([smi, f"--query-gpu={query}", "--format=csv,noheader,nounits"]) or ""


def http_ok(url, timeout=2):
    """Prüft ob HTTP-Service erreichbar ist"""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.getcode() < 300
    except Exception:
        return False


def get_cpu_ram():
    """Sammelt CPU- und RAM-Info"""
    if platform.system() == "Linux":
        cpu = run("lscpu")
        model = re.search(r"Model name:\s*(.*)", cpu)
        cores = re.search(r"^CPU\(s\):\s*(\d+)", cpu, re.M)
        
        with open("/proc/meminfo") as f:
            memkib = int(re.search(r"MemTotal:\s*(\d+)", f.read()).group(1))
        
        return (
            model.group(1).strip() if model else platform.processor(),
            int(cores.group(1)) if cores else os.cpu_count(),
            memkib * 1024
        )
    else:
        # Windows / Fallback
        return (platform.processor() or platform.machine(), os.cpu_count() or 0, 0)


def get_cuda_driver():
    """Sammelt CUDA-Treiber-Info"""
    smi = shutil.which("nvidia-smi")
    if not smi:
        return ("none", "none")
    
    drv = run([smi, "--query", "-i=0", "--format=csv,noheader", "--query-gpu=driver_version"]) or "unknown"
    raw = run(smi)
    m = re.search(r"CUDA Version:\s*([0-9.]+)", raw)
    
    return (drv, m.group(1) if m else "unknown")


def service_up():
    """Prüft Service-Verfügbarkeit"""
    st = []
    
    # Ollama: /api/tags quick check
    st.append(("ollama", http_ok(OLLAMA + "/api/tags")))
    
    # Chroma: try /api/v1/heartbeat else root
    ok_ch = http_ok(CHROMA + "/api/v1/heartbeat") or http_ok(CHROMA)
    st.append(("chroma", ok_ch))
    
    # Piper: binary present
    st.append(("piper", bool(shutil.which(PIPER_BIN))))
    
    # WhisperX: python import quick check
    try:
        subprocess.check_call(
            [sys.executable, "-c", "import whisperx"], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL, 
            timeout=3
        )
        st.append(("whisperx", True))
    except Exception:
        st.append(("whisperx", False))
    
    return st


def main():
    """Haupt-Funktion"""
    cpu_model, cpu_cores, ram_bytes = get_cpu_ram()
    drv, cuda = get_cuda_driver()
    
    names = nvidia_smi_q("name").splitlines() if nvidia_smi_q("name") else []
    vram = nvidia_smi_q("memory.total").splitlines() if nvidia_smi_q("memory.total") else []
    
    lines = []
    
    # CPU & RAM
    lines.append(f'tom_host_cpu_info{{model="{cpu_model}",cores="{cpu_cores}"}} 1')
    if ram_bytes:
        lines.append(f"tom_host_ram_bytes {ram_bytes}")
    
    # GPU info
    lines.append(f"tom_gpu_count {len(names)}")
    if drv or cuda:
        lines.append(f'tom_gpu_driver_info{{driver="{drv}",cuda="{cuda}"}} 1')
    
    max_vram_gb = 0.0
    for i, nm in enumerate(names):
        v = 0
        try:
            v = int(vram[i]) if i < len(vram) else 0
        except:
            pass
        
        if v:
            max_vram_gb = max(max_vram_gb, v / 1024.0)
            bytes_ = v * 1024 * 1024
            safe_name = nm.replace('"', '').replace('\\', '')
            lines.append(f'tom_gpu_vram_bytes{{index="{i}",name="{safe_name}"}} {bytes_}')
    
    # Services
    ups = dict(service_up())
    for k, ok in ups.items():
        lines.append(f'tom_service_up{{name="{k}"}} {1 if ok else 0}')
    
    # LLM model info (optional: parse tags)
    llm_name = ""
    if ups.get("ollama"):
        try:
            data = json.loads(run(f"curl -s {OLLAMA}/api/tags"))
            if isinstance(data, dict) and data.get("models"):
                llm_name = data["models"][0].get("name", "")
        except Exception:
            pass
    
    if llm_name:
        lines.append(f'tom_llm_info{{name="{llm_name}"}} 1')
    else:
        lines.append('tom_llm_info{name="unknown"} 0')
    
    # Readiness gates
    realtime = int(
        max_vram_gb >= 12.0 
        and (ram_bytes or 0) >= 32 * 1024 * 1024 * 1024 
        and all(ups.get(k, False) for k in ("ollama", "whisperx", "piper", "chroma"))
    )
    
    single = int(
        max_vram_gb >= 8.0 
        and (ram_bytes or 0) >= 16 * 1024 * 1024 * 1024 
        and all(ups.get(k, False) for k in ("ollama", "piper"))
    )
    
    lines.append(f"tom_readiness_realtime {realtime}")
    lines.append(f"tom_readiness_single_agent {single}")
    
    # Timestamp für Debug
    lines.append(f"tom_host_inventory_timestamp_seconds {int(time.time())}")
    
    # Ausgabe
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    
    print(f"Host inventory written to {OUT}")


if __name__ == "__main__":
    main()

