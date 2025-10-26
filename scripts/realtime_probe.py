"""
TOM v3.0 - Realtime Probe
E2E-Latenztests für Realtime-API mit Fallback
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List

import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Konfiguration
WS_URL = os.getenv('WS_URL', 'ws://localhost:8081/ws/stream')
TEST_CALL_ID = f"probe_{int(time.time())}"
DEV_ALLOW_NO_JWT = os.getenv('DEV_ALLOW_NO_JWT', 'true').lower() == 'true'


class RealtimeProbe:
    """Realtime Probe für E2E-Latenztests"""
    
    def __init__(self):
        self.results = {
            'call_id': TEST_CALL_ID,
            'start_time': datetime.now().isoformat(),
            'first_token_ms': None,
            'first_audio_ms': None,
            'e2e_ms': None,
            'backend': None,
            'status': 'running'
        }
        self.stt_timestamp = None
        self.first_token_timestamp = None
        self.first_audio_timestamp = None
        
    async def run_test(self):
        """Führt E2E-Test durch"""
        logger.info(f"Starting Realtime Probe for {TEST_CALL_ID}")
        
        try:
            async with websockets.connect(WS_URL + f"/{TEST_CALL_ID}") as ws:
                # Connected-Event empfangen
                connected = await ws.recv()
                logger.info(f"Connected: {connected}")
                
                # Backend-Typ extrahieren
                data = json.loads(connected)
                if 'config' in data:
                    self.results['backend'] = 'provider' if data['config'].get('stt_mode') == 'provider' else 'local'
                
                # Audio-Chunk senden (Mock-Test)
                audio_chunk = b'\x00' * 640  # 20ms @ 16kHz
                base64_audio = b"fake_base64_audio".decode()
                
                event = {
                    'type': 'audio_chunk',
                    'audio': base64_audio,
                    'timestamp': time.time(),
                    'audio_length': len(audio_chunk)
                }
                
                await ws.send(json.dumps(event))
                self.stt_timestamp = time.time()
                
                # Events empfangen und Timing messen
                async for message in ws:
                    try:
                        event = json.loads(message)
                        await self._handle_event(event)
                        
                        # Test beenden wenn TTS-Complete
                        if event.get('type') == 'tts_complete':
                            break
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON: {message}")
                        
        except Exception as e:
            logger.error(f"Probe error: {e}")
            self.results['status'] = 'failed'
            self.results['error'] = str(e)
            return 1
        
        # Ergebnisse berechnen
        self._calculate_results()
        
        # Ergebnisse ausgeben
        self._print_results()
        
        # Exit-Code basierend auf Latenz
        return self._get_exit_code()
    
    async def _handle_event(self, event: dict):
        """Verarbeitet Realtime-Event"""
        event_type = event.get('type')
        
        if event_type == 'stt_final':
            logger.info("STT Final received")
            self.stt_timestamp = time.time()
            
        elif event_type == 'llm_token':
            if self.first_token_timestamp is None:
                self.first_token_timestamp = time.time()
                logger.info("First LLM token received")
                
        elif event_type == 'tts_audio':
            if self.first_audio_timestamp is None:
                self.first_audio_timestamp = time.time()
                logger.info("First TTS audio received")
                
        elif event_type == 'barge_in_ack':
            logger.info("Barge-in acknowledged")
            
        elif event_type == 'provider_error':
            logger.warning(f"Provider error: {event.get('message')}")
    
    def _calculate_results(self):
        """Berechnet Latenz-Ergebnisse"""
        if self.stt_timestamp and self.first_token_timestamp:
            self.results['first_token_ms'] = (self.first_token_timestamp - self.stt_timestamp) * 1000
            
        if self.first_token_timestamp and self.first_audio_timestamp:
            self.results['first_audio_ms'] = (self.first_audio_timestamp - self.first_token_timestamp) * 1000
            
        if self.stt_timestamp and self.first_audio_timestamp:
            self.results['e2e_ms'] = (self.first_audio_timestamp - self.stt_timestamp) * 1000
            
        self.results['end_time'] = datetime.now().isoformat()
        self.results['status'] = 'completed'
    
    def _print_results(self):
        """Gibt Ergebnisse aus"""
        print("\n" + "="*60)
        print("REALTIME PROBE RESULTS")
        print("="*60)
        print(f"Call ID: {self.results['call_id']}")
        print(f"Backend: {self.results['backend']}")
        print(f"Status: {self.results['status']}")
        
        if self.results['first_token_ms']:
            print(f"First Token: {self.results['first_token_ms']:.1f}ms")
            
        if self.results['first_audio_ms']:
            print(f"First Audio: {self.results['first_audio_ms']:.1f}ms")
            
        if self.results['e2e_ms']:
            print(f"E2E Latency: {self.results['e2e_ms']:.1f}ms")
            
        print("="*60)
        
        # JSON-Export
        self._export_json()
    
    def _export_json(self):
        """Exportiert Ergebnisse als JSON"""
        output_file = f"data/test_results/probe_{self.results['call_id']}.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
            
        logger.info(f"Results exported to {output_file}")
    
    def _get_exit_code(self) -> int:
        """Bestimmt Exit-Code basierend auf Latenz-Zielen"""
        e2e_ms = self.results.get('e2e_ms')
        
        if e2e_ms is None:
            return 1  # Keine Latenz-Messung
            
        # Exit-Codes:
        # 0: Erfolg (E2E < 500ms)
        # 1: Warnung (500ms <= E2E < 800ms)
        # 2: Fehler (E2E >= 800ms)
        
        if e2e_ms < 500:
            logger.info("✓ Probe PASSED (E2E < 500ms)")
            return 0
        elif e2e_ms < 800:
            logger.warning("⚠ Probe WARNING (500ms <= E2E < 800ms)")
            return 1
        else:
            logger.error("✗ Probe FAILED (E2E >= 800ms)")
            return 2


async def main():
    """Hauptfunktion"""
    probe = RealtimeProbe()
    exit_code = await probe.run_test()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
