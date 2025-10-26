#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOM v3.0 - E2E Tests für Realtime-Pipeline (ohne Mocks)
Echte Tests der kompletten Sprachkette
"""

import asyncio
import json
import logging
import os
import time
import websockets
import numpy as np
import base64
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class RealtimeE2ETest:
    """E2E-Test für Realtime-Pipeline"""
    
    def __init__(self):
        self.ws_url = "ws://localhost:8081/ws/stream/test-e2e-001"
        self.jwt_token = "dev-token"  # DEV-Modus
        self.websocket = None
        self.test_results = {}
        self.events_received = []
        
    async def run_test(self) -> Dict:
        """Kompletter E2E-Test durchführen"""
        logger.info("🚀 Starte E2E-Test für Realtime-Pipeline")
        
        try:
            # 1. Verbindung testen
            await self.test_connection()
            
            # 2. Audio-Pipeline testen
            await self.test_audio_pipeline()
            
            # 3. Barge-In testen
            await self.test_barge_in()
            
            # 4. Latenz-Metriken sammeln
            await self.collect_metrics()
            
            # 5. Ergebnisse bewerten
            results = self.evaluate_results()
            
            logger.info("✅ E2E-Test abgeschlossen")
            return results
            
        except Exception as e:
            logger.error(f"❌ E2E-Test fehlgeschlagen: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': self.test_results
            }
        finally:
            await self.cleanup()
    
    async def test_connection(self):
        """WebSocket-Verbindung testen"""
        logger.info("🔌 Teste WebSocket-Verbindung...")
        
        start_time = time.time()
        
        try:
            self.websocket = await websockets.connect(
                self.ws_url,
                subprotocols=['realtime-v1']
            )
            
            # JWT senden
            await self.websocket.send(json.dumps({
                'jwt': self.jwt_token
            }))
            
            # Connected-Event abwarten
            response = await asyncio.wait_for(
                self.websocket.recv(), 
                timeout=5.0
            )
            
            data = json.loads(response)
            if data.get('type') == 'connected':
                connection_time = (time.time() - start_time) * 1000
                self.test_results['connection'] = {
                    'success': True,
                    'latency_ms': connection_time,
                    'call_id': data.get('call_id')
                }
                logger.info(f"✅ Verbindung erfolgreich: {connection_time:.1f}ms")
            else:
                raise Exception(f"Unerwartete Antwort: {data}")
                
        except Exception as e:
            self.test_results['connection'] = {
                'success': False,
                'error': str(e)
            }
            raise
    
    async def test_audio_pipeline(self):
        """Komplette Audio-Pipeline testen"""
        logger.info("🎤 Teste Audio-Pipeline...")
        
        # Test-Audio generieren (1 Sekunde Sinus-Welle)
        test_audio = self.generate_test_audio(duration=1.0, frequency=440)
        
        # Pipeline-Start
        pipeline_start = time.time()
        
        # Audio-Chunks senden
        chunk_size = 320  # 20ms bei 16kHz
        for i in range(0, len(test_audio), chunk_size):
            chunk = test_audio[i:i + chunk_size]
            
            # Base64 kodieren
            audio_bytes = chunk.astype(np.int16).tobytes()
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
        
        # Events sammeln
        await self.collect_pipeline_events(timeout=10.0)
        
        pipeline_end = time.time()
        pipeline_duration = (pipeline_end - pipeline_start) * 1000
        
        self.test_results['audio_pipeline'] = {
            'success': True,
            'duration_ms': pipeline_duration,
            'events_count': len(self.events_received)
        }
        
        logger.info(f"✅ Audio-Pipeline: {pipeline_duration:.1f}ms, {len(self.events_received)} Events")
    
    async def test_barge_in(self):
        """Barge-In-Funktionalität testen"""
        logger.info("⚡ Teste Barge-In...")
        
        barge_in_start = time.time()
        
        # Barge-In senden
        await self.websocket.send(json.dumps({
            'type': 'barge_in',
            'timestamp': time.time()
        }))
        
        # Barge-In-Acknowledgement abwarten
        ack_received = False
        timeout = 2.0
        
        try:
            while time.time() - barge_in_start < timeout:
                response = await asyncio.wait_for(
                    self.websocket.recv(), 
                    timeout=0.1
                )
                
                data = json.loads(response)
                if data.get('type') == 'barge_in_ack':
                    ack_received = True
                    break
                    
        except asyncio.TimeoutError:
            pass
        
        barge_in_duration = (time.time() - barge_in_start) * 1000
        
        self.test_results['barge_in'] = {
            'success': ack_received,
            'latency_ms': barge_in_duration,
            'ack_received': ack_received
        }
        
        if ack_received:
            logger.info(f"✅ Barge-In: {barge_in_duration:.1f}ms")
        else:
            logger.warning(f"⚠️ Barge-In: Kein ACK nach {barge_in_duration:.1f}ms")
    
    async def collect_pipeline_events(self, timeout: float = 5.0):
        """Pipeline-Events sammeln"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = await asyncio.wait_for(
                    self.websocket.recv(), 
                    timeout=0.1
                )
                
                data = json.loads(response)
                self.events_received.append({
                    'type': data.get('type'),
                    'timestamp': time.time(),
                    'data': data
                })
                
                # Pipeline-Ende erkennen
                if data.get('type') in ['tts_complete', 'pipeline_complete']:
                    break
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.warning(f"Event-Sammlung Fehler: {e}")
                break
    
    async def collect_metrics(self):
        """Latenz-Metriken sammeln"""
        metrics = {}
        
        # Event-Zeitpunkte extrahieren
        event_times = {}
        for event in self.events_received:
            event_type = event['type']
            if event_type not in event_times:
                event_times[event_type] = event['timestamp']
        
        # Metriken berechnen
        if 'stt_final' in event_times and 'llm_token' in event_times:
            metrics['stt_to_llm_ms'] = (event_times['llm_token'] - event_times['stt_final']) * 1000
        
        if 'llm_token' in event_times and 'tts_audio' in event_times:
            metrics['llm_to_tts_ms'] = (event_times['tts_audio'] - event_times['llm_token']) * 1000
        
        if 'stt_final' in event_times and 'tts_complete' in event_times:
            metrics['e2e_ms'] = (event_times['tts_complete'] - event_times['stt_final']) * 1000
        
        self.test_results['metrics'] = metrics
        
        logger.info(f"📊 Metriken: {metrics}")
    
    def generate_test_audio(self, duration: float = 1.0, frequency: float = 440) -> np.ndarray:
        """Test-Audio generieren (Sinus-Welle)"""
        sample_rate = 16000
        samples = int(duration * sample_rate)
        
        # Sinus-Welle
        t = np.linspace(0, duration, samples, False)
        audio = np.sin(2 * np.pi * frequency * t)
        
        # Normalisieren und zu Int16 konvertieren
        audio = (audio * 0.3 * 32767).astype(np.int16)
        
        return audio
    
    def evaluate_results(self) -> Dict:
        """Testergebnisse bewerten"""
        results = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'tests': self.test_results,
            'summary': {}
        }
        
        # Erfolgskriterien prüfen
        success_criteria = {
            'connection_latency_ms': 1000,  # < 1s
            'stt_to_llm_ms': 300,          # < 300ms
            'llm_to_tts_ms': 200,          # < 200ms
            'e2e_ms': 800,                 # < 800ms
            'barge_in_ms': 120             # < 120ms
        }
        
        summary = {}
        
        # Verbindung
        if 'connection' in self.test_results:
            conn = self.test_results['connection']
            if conn['success']:
                summary['connection'] = f"✅ {conn['latency_ms']:.1f}ms"
            else:
                summary['connection'] = f"❌ {conn.get('error', 'Unknown error')}"
                results['success'] = False
        
        # Metriken
        if 'metrics' in self.test_results:
            metrics = self.test_results['metrics']
            
            for metric, threshold in success_criteria.items():
                if metric in metrics:
                    value = metrics[metric]
                    if value <= threshold:
                        summary[metric] = f"✅ {value:.1f}ms (≤ {threshold}ms)"
                    else:
                        summary[metric] = f"⚠️ {value:.1f}ms (> {threshold}ms)"
                        results['success'] = False
        
        # Barge-In
        if 'barge_in' in self.test_results:
            barge_in = self.test_results['barge_in']
            if barge_in['success']:
                summary['barge_in'] = f"✅ {barge_in['latency_ms']:.1f}ms"
            else:
                summary['barge_in'] = f"❌ Kein ACK"
                results['success'] = False
        
        results['summary'] = summary
        
        return results
    
    async def cleanup(self):
        """Cleanup nach Test"""
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()


async def main():
    """Hauptfunktion für E2E-Test"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test = RealtimeE2ETest()
    results = await test.run_test()
    
    # Ergebnisse ausgeben
    print("\n" + "="*60)
    print("🎯 TOM v3.0 E2E-Test Ergebnisse")
    print("="*60)
    
    if results['success']:
        print("✅ GESAMTERGEBNIS: ERFOLGREICH")
    else:
        print("❌ GESAMTERGEBNIS: FEHLGESCHLAGEN")
    
    print("\n📊 Zusammenfassung:")
    for key, value in results['summary'].items():
        print(f"  {key}: {value}")
    
    print(f"\n📝 Vollständige Ergebnisse:")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    # Exit-Code basierend auf Erfolg
    exit(0 if results['success'] else 1)


if __name__ == '__main__':
    asyncio.run(main())
