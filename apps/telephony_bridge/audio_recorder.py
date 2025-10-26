#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOM v3.0 - Audio Recording & Qualitätsprüfung
DSGVO-konforme Aufzeichnung für interne Qualitätstests
"""

import os
import time
import base64
import wave
import threading
import json
import logging
from pathlib import Path
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

# Konfiguration
RECORD_AUDIO = os.getenv("RECORD_AUDIO", "false").lower() == "true"
RECORD_DIR = Path(os.getenv("RECORD_PATH", "./data/recordings")).resolve()
RETENTION_HOURS = int(os.getenv("RECORD_RETENTION_HOURS", "24"))

class WavSink:
    """WAV-Audio-Sink für Aufzeichnung"""
    
    def __init__(self, call_id: str):
        self.call_id = call_id
        self.dir = RECORD_DIR / call_id
        self.dir.mkdir(parents=True, exist_ok=True)
        
        # WAV-Datei
        self.fpath = self.dir / f"{call_id}.wav"
        self._wf = wave.open(str(self.fpath), "wb")
        self._wf.setnchannels(1)  # Mono
        self._wf.setsampwidth(2)  # 16-bit
        self._wf.setframerate(16000)  # 16kHz
        
        # Thread-Sicherheit
        self._lock = threading.Lock()
        
        # Metadaten
        self.start_time = time.time()
        self.meta_file = self.dir / "meta.txt"
        self.meta_file.write_text(
            f"call_id={call_id}\n"
            f"start_ts={self.start_time}\n"
            f"start_time={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time))}\n",
            encoding="utf-8"
        )
        
        logger.info(f"Audio-Recording gestartet: {self.fpath}")
    
    def write_pcm16_16k(self, audio_bytes: bytes):
        """PCM16 16kHz Audio-Daten schreiben"""
        with self._lock:
            try:
                self._wf.writeframes(audio_bytes)
            except Exception as e:
                logger.error(f"Fehler beim Schreiben von Audio: {e}")
    
    def close(self):
        """Recording beenden und Metadaten aktualisieren"""
        with self._lock:
            try:
                self._wf.close()
            except Exception as e:
                logger.error(f"Fehler beim Schließen der WAV-Datei: {e}")
        
        # Metadaten vervollständigen
        end_time = time.time()
        duration = end_time - self.start_time
        
        try:
            existing_meta = self.meta_file.read_text(encoding="utf-8")
            self.meta_file.write_text(
                existing_meta +
                f"end_ts={end_time}\n"
                f"end_time={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))}\n"
                f"duration_sec={duration:.2f}\n"
                f"sample_rate=16000\n"
                f"channels=1\n"
                f"bit_depth=16\n",
                encoding="utf-8"
            )
            
            logger.info(f"Audio-Recording beendet: {duration:.2f}s, {self.fpath}")
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Metadaten: {e}")


class AudioRecorder:
    """Audio-Recorder-Manager"""
    
    def __init__(self):
        self.active_recordings: dict[str, WavSink] = {}
        
    def start_recording(self, call_id: str) -> Optional[WavSink]:
        """Recording für Call-ID starten"""
        if not RECORD_AUDIO:
            return None
            
        try:
            sink = WavSink(call_id)
            self.active_recordings[call_id] = sink
            return sink
        except Exception as e:
            logger.error(f"Fehler beim Starten der Aufzeichnung für {call_id}: {e}")
            return None
    
    def stop_recording(self, call_id: str):
        """Recording für Call-ID beenden"""
        if call_id in self.active_recordings:
            try:
                self.active_recordings[call_id].close()
                del self.active_recordings[call_id]
            except Exception as e:
                logger.error(f"Fehler beim Beenden der Aufzeichnung für {call_id}: {e}")
    
    def cleanup_old_recordings(self):
        """Alte Aufnahmen löschen (DSGVO-konform)"""
        if not RECORD_AUDIO:
            return
            
        try:
            cutoff_time = time.time() - (RETENTION_HOURS * 3600)
            cleaned_count = 0
            
            for subdir in RECORD_DIR.glob("*"):
                if not subdir.is_dir():
                    continue
                    
                try:
                    meta_file = subdir / "meta.txt"
                    if meta_file.exists():
                        # Start-Zeit aus Metadaten lesen
                        meta_content = meta_file.read_text(encoding="utf-8")
                        for line in meta_content.splitlines():
                            if line.startswith("start_ts="):
                                start_ts = float(line.split("=", 1)[1])
                                if start_ts < cutoff_time:
                                    # Verzeichnis löschen
                                    import shutil
                                    shutil.rmtree(subdir, ignore_errors=True)
                                    cleaned_count += 1
                                    logger.info(f"Alte Aufnahme gelöscht: {subdir}")
                                    break
                except Exception as e:
                    logger.warning(f"Fehler beim Cleanup von {subdir}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleanup abgeschlossen: {cleaned_count} alte Aufnahmen gelöscht")
                
        except Exception as e:
            logger.error(f"Fehler beim Cleanup alter Aufnahmen: {e}")


# Globale Instanz
audio_recorder = AudioRecorder()
