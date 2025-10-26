#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOM v3.0 - Audio Recording Test
Testet die Audio-Aufzeichnung und Qualitätsprüfung
"""

import asyncio
import json
import time
import websockets
import base64
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class AudioRecordingTest:
    """Test für Audio-Recording-Funktionalität"""
    
    def __init__(self):
        self.ws_url = "ws://localhost:8081/ws/stream/test-recording-001"
        self.jwt_token = "dev-token"
        self.websocket = None
        
    async def run_test(self):
        """Kompletter Recording-Test"""
        logger.info("🎤 Starte Audio-Recording-Test")
        
        try:
            # Verbindung herstellen
            await self.connect()
            
            # Test-Audio generieren und senden
            await self.send_test_audio()
            
            # Warten auf Verarbeitung
            await asyncio.sleep(2)
            
            # Verbindung schließen
            await self.disconnect()
            
            # Qualitätsprüfung durchführen
            await self.check_recording_quality()
            
            logger.info("✅ Audio-Recording-Test abgeschlossen")
            
        except Exception as e:
            logger.error(f"❌ Test fehlgeschlagen: {e}")
    
    async def connect(self):
        """WebSocket-Verbindung herstellen"""
        logger.info("🔌 Verbinde mit Server...")
        
        self.websocket = await websockets.connect(self.ws_url)
        
        # JWT senden
        await self.websocket.send(json.dumps({
            'jwt': self.jwt_token
        }))
        
        # Connected-Event abwarten
        response = await self.websocket.recv()
        data = json.loads(response)
        
        if data.get('type') == 'connected':
            logger.info(f"✅ Verbunden: {data.get('call_id')}")
        else:
            raise Exception(f"Unerwartete Antwort: {data}")
    
    async def send_test_audio(self):
        """Test-Audio generieren und senden"""
        logger.info("🎵 Generiere und sende Test-Audio...")
        
        # Test-Audio: 2 Sekunden Sinus-Welle (440Hz)
        duration = 2.0
        sample_rate = 16000
        frequency = 440
        
        samples = int(duration * sample_rate)
        t = np.linspace(0, duration, samples, False)
        audio = np.sin(2 * np.pi * frequency * t)
        
        # Normalisieren und zu Int16 konvertieren
        audio = (audio * 0.5 * 32767).astype(np.int16)
        
        # In Chunks aufteilen (20ms = 320 Samples)
        chunk_size = 320
        for i in range(0, len(audio), chunk_size):
            chunk = audio[i:i + chunk_size]
            
            # Base64 kodieren
            audio_bytes = chunk.tobytes()
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            # Chunk senden
            message = {
                'type': 'audio_chunk',
                'audio': audio_b64,
                'timestamp': time.time(),
                'audio_length': len(chunk)
            }
            
            await self.websocket.send(json.dumps(message))
            
            # Kleine Pause zwischen Chunks
            await asyncio.sleep(0.02)  # 20ms
        
        logger.info("✅ Test-Audio gesendet")
    
    async def disconnect(self):
        """Verbindung schließen"""
        if self.websocket:
            await self.websocket.close()
            logger.info("🔌 Verbindung geschlossen")
    
    async def check_recording_quality(self):
        """Aufgenommene Datei prüfen"""
        logger.info("🔍 Prüfe Aufnahme-Qualität...")
        
        # Recording-Verzeichnis finden
        recordings_dir = Path("data/recordings")
        if not recordings_dir.exists():
            logger.warning("⚠️ Kein Recordings-Verzeichnis gefunden")
            return
        
        # Neueste Aufnahme finden
        call_dirs = list(recordings_dir.glob("test-recording-*"))
        if not call_dirs:
            logger.warning("⚠️ Keine Test-Aufnahmen gefunden")
            return
        
        latest_dir = max(call_dirs, key=lambda p: p.stat().st_mtime)
        wav_file = latest_dir / f"{latest_dir.name}.wav"
        
        if not wav_file.exists():
            logger.warning(f"⚠️ WAV-Datei nicht gefunden: {wav_file}")
            return
        
        logger.info(f"📁 Gefundene Aufnahme: {wav_file}")
        
        # Qualitätsprüfung durchführen
        try:
            import subprocess
            result = subprocess.run([
                "python", "scripts/qc_audio.py", str(wav_file)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                qc_data = json.loads(result.stdout)
                logger.info("📊 Qualitätsprüfung:")
                logger.info(f"  RMS: {qc_data['metrics']['rms']}")
                logger.info(f"  Peak: {qc_data['metrics']['peak']}")
                logger.info(f"  SNR: {qc_data['metrics']['snr_db_est']} dB")
                logger.info(f"  Qualität: {qc_data['quality']['rating']}")
                
                for advice in qc_data['advice']:
                    logger.info(f"  💡 {advice}")
            else:
                logger.error(f"❌ QC-Fehler: {result.stderr}")
                
        except Exception as e:
            logger.error(f"❌ Fehler bei Qualitätsprüfung: {e}")


async def main():
    """Hauptfunktion"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test = AudioRecordingTest()
    await test.run_test()


if __name__ == '__main__':
    asyncio.run(main())
