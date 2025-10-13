#!/usr/bin/env python3
"""
TOM v3.0 - Realtime Probe Script für Loop Closure Latenzmessung

Misst die Latenz der kompletten Realtime-Pipeline:
Frontend → WebSocket → Mock-STT/LLM/TTS → Frontend

CSB v1 Compliance:
- UTF-8 Encoding für alle Ausgaben
- JSON-Export mit korrektem Encoding
- SLO-Verifikation (< 1500ms End-to-End für Mock)
"""
import asyncio
import time
import json
import os
import sys
import base64
from datetime import datetime
from typing import Dict, List, Any, Optional
import websockets

# UTF-8 Encoding sicherstellen
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

class RealtimeProbe:
    """
    Realtime-Probe für Loop Closure Latenzmessung der TOM v3.0 Pipeline
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialisiert die Realtime-Probe
        
        Args:
            config: Konfigurationsdictionary
        """
        self.config = config
        self.results = []
        self.websocket = None
        self.call_id = f"probe_{int(time.time())}"
        
        # SLO-Ziele für Mock-Modus
        self.slo_target_latency = 1500  # ms (höher für Mock)
        self.slo_accuracy = 0.90
        
        # Messpunkte
        self.timestamps = {}
        
    async def connect_websocket(self):
        """Verbindet zum WebSocket-Server"""
        try:
            websocket_url = self.config.get('websocket_url', 'ws://localhost:8080/ws/stream')
            jwt_token = self.config.get('jwt_token', 'dev_token')
            
            # WebSocket-URL mit Call-ID und JWT
            full_url = f"{websocket_url}/{self.call_id}?t={jwt_token}"
            
            self.websocket = await websockets.connect(full_url)
            print(f"✅ WebSocket-Verbindung erfolgreich: {self.call_id}")
            
        except Exception as e:
            print(f"❌ WebSocket-Verbindungsfehler: {e}")
            raise
    
    async def send_ping(self) -> float:
        """Sendet Ping und misst Pong-Latenz"""
        try:
            ping_start = time.time()
            
            ping_message = {
                "type": "ping",
                "ts": int(ping_start * 1000)
            }
            
            await self.websocket.send(json.dumps(ping_message))
            
            # Warte auf Pong
            response = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
            pong_data = json.loads(response)
            
            if pong_data.get('type') == 'pong':
                ping_end = time.time()
                latency = (ping_end - ping_start) * 1000
                print(f"📡 Ping/Pong-Latenz: {latency:.1f}ms")
                return latency
            else:
                print("❌ Ungültige Pong-Antwort")
                return -1
                
        except asyncio.TimeoutError:
            print("❌ Ping/Pong-Timeout")
            return -1
        except Exception as e:
            print(f"❌ Ping/Pong-Fehler: {e}")
            return -1
    
    async def send_audio_chunk(self) -> Dict[str, float]:
        """Sendet Audio-Chunk und misst komplette Pipeline-Latenz"""
        try:
            # Generiere Mock-Audio-Daten (1 Sekunde Stille)
            silence_samples = 16000  # 1 Sekunde bei 16kHz
            silence_data = b'\x00\x00' * silence_samples
            audio_b64 = base64.b64encode(silence_data).decode('utf-8')
            
            # Start-Zeit für komplette Pipeline
            pipeline_start = time.time()
            
            # Audio-Chunk senden
            audio_message = {
                "type": "audio_chunk",
                "ts": int(pipeline_start * 1000),
                "data": audio_b64,
                "format": "pcm16_16k"
            }
            
            await self.websocket.send(json.dumps(audio_message))
            print("🎤 Audio-Chunk gesendet")
            
            # Messpunkte für verschiedene Events
            stt_final_time = None
            first_llm_token_time = None
            first_tts_audio_time = None
            turn_end_time = None
            
            # Warte auf Events mit Timeout
            timeout = 10.0  # 10 Sekunden Timeout
            start_wait = time.time()
            
            while time.time() - start_wait < timeout:
                try:
                    response = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    event_data = json.loads(response)
                    event_type = event_data.get('type')
                    
                    current_time = time.time()
                    
                    if event_type == 'stt_final' and stt_final_time is None:
                        stt_final_time = current_time
                        print(f"✅ STT Final erhalten: {event_data.get('text', '')}")
                        
                    elif event_type == 'llm_token' and first_llm_token_time is None:
                        first_llm_token_time = current_time
                        print(f"🤖 Erstes LLM-Token: {event_data.get('text', '')}")
                        
                    elif event_type == 'tts_audio' and first_tts_audio_time is None:
                        first_tts_audio_time = current_time
                        print(f"🔊 Erstes TTS-Audio erhalten")
                        
                    elif event_type == 'turn_end' and turn_end_time is None:
                        turn_end_time = current_time
                        print(f"🏁 Turn-Ende erhalten")
                        break  # Pipeline abgeschlossen
                        
                except asyncio.TimeoutError:
                    continue
            
            # Berechne Latenzen
            latencies = {}
            
            if stt_final_time:
                latencies['stt_final_ms'] = (stt_final_time - pipeline_start) * 1000
            else:
                latencies['stt_final_ms'] = -1
                
            if first_llm_token_time:
                latencies['llm_first_token_ms'] = (first_llm_token_time - pipeline_start) * 1000
            else:
                latencies['llm_first_token_ms'] = -1
                
            if first_tts_audio_time:
                latencies['tts_first_audio_ms'] = (first_tts_audio_time - pipeline_start) * 1000
            else:
                latencies['tts_first_audio_ms'] = -1
                
            if turn_end_time:
                latencies['e2e_ms'] = (turn_end_time - pipeline_start) * 1000
            else:
                latencies['e2e_ms'] = -1
            
            return latencies
            
        except Exception as e:
            print(f"❌ Audio-Chunk-Fehler: {e}")
            return {
                'stt_final_ms': -1,
                'llm_first_token_ms': -1,
                'tts_first_audio_ms': -1,
                'e2e_ms': -1
            }
    
    async def run_benchmark(self, iterations: int = 5) -> List[Dict[str, Any]]:
        """
        Führt Benchmark-Tests durch
        
        Args:
            iterations: Anzahl der Test-Iterationen
            
        Returns:
            Liste der Messergebnisse
        """
        print(f"🚀 Starte Loop Closure Benchmark mit {iterations} Iterationen...")
        
        results = []
        for i in range(iterations):
            print(f"\n📊 Iteration {i+1}/{iterations}")
            
            # Ping/Pong-Test
            ping_latency = await self.send_ping()
            
            # Audio-Chunk-Test
            latencies = await self.send_audio_chunk()
            
            # Ergebnis zusammenstellen
            result = {
                'iteration': i + 1,
                'timestamp': datetime.now().isoformat(),
                'ping_latency_ms': ping_latency,
                **latencies
            }
            
            results.append(result)
            
            # Ausgabe
            print(f"   📡 Ping/Pong: {ping_latency:.1f}ms")
            print(f"   ✅ STT Final: {latencies['stt_final_ms']:.1f}ms")
            print(f"   🤖 LLM First Token: {latencies['llm_first_token_ms']:.1f}ms")
            print(f"   🔊 TTS First Audio: {latencies['tts_first_audio_ms']:.1f}ms")
            print(f"   🏁 End-to-End: {latencies['e2e_ms']:.1f}ms")
            
            # Pause zwischen Tests
            if i < iterations - 1:
                await asyncio.sleep(2.0)
        
        return results
    
    def verify_slo_compliance(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verifiziert SLO-Compliance für Loop Closure
        
        Args:
            results: Messergebnisse
            
        Returns:
            SLO-Compliance-Status
        """
        # Filtere gültige Ergebnisse (ohne -1)
        valid_results = [r for r in results if r['e2e_ms'] > 0]
        
        if not valid_results:
            return {
                'avg_e2e_ms': -1,
                'max_e2e_ms': -1,
                'min_e2e_ms': -1,
                'compliance_rate': 0.0,
                'overall_compliant': False
            }
        
        e2e_latencies = [r['e2e_ms'] for r in valid_results]
        avg_latency = sum(e2e_latencies) / len(e2e_latencies)
        max_latency = max(e2e_latencies)
        min_latency = min(e2e_latencies)
        
        # SLO-Checks
        latency_compliant = avg_latency < self.slo_target_latency
        max_latency_compliant = max_latency < self.slo_target_latency * 1.5
        
        compliance_rate = sum(1 for lat in e2e_latencies if lat < self.slo_target_latency) / len(e2e_latencies)
        accuracy_compliant = compliance_rate >= self.slo_accuracy
        
        return {
            'avg_e2e_ms': avg_latency,
            'max_e2e_ms': max_latency,
            'min_e2e_ms': min_latency,
            'compliance_rate': compliance_rate,
            'latency_compliant': latency_compliant,
            'max_latency_compliant': max_latency_compliant,
            'accuracy_compliant': accuracy_compliant,
            'overall_compliant': latency_compliant and max_latency_compliant and accuracy_compliant
        }
    
    def export_json(self, results: List[Dict[str, Any]], filename: str = None):
        """
        Exportiert Ergebnisse als JSON mit UTF-8 Encoding
        
        Args:
            results: Messergebnisse
            filename: Ausgabedatei (optional)
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"realtime_probe_results_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(results, jsonfile, indent=2, ensure_ascii=False)
            
            print(f"📊 Ergebnisse exportiert nach: {filename}")
            
        except Exception as e:
            print(f"❌ JSON-Export-Fehler: {e}")
    
    async def cleanup(self):
        """Räumt Verbindungen auf"""
        if self.websocket:
            await self.websocket.close()

async def main():
    """Hauptfunktion"""
    print("🎯 TOM v3.0 Realtime Loop Closure Probe gestartet")
    
    # Konfiguration
    config = {
        'websocket_url': os.getenv('WEBSOCKET_URL', 'ws://localhost:8080/ws/stream'),
        'jwt_token': os.getenv('JWT_TOKEN', 'dev_token'),
        'iterations': int(os.getenv('PROBE_ITERATIONS', '5'))
    }
    
    probe = RealtimeProbe(config)
    
    try:
        # WebSocket verbinden
        await probe.connect_websocket()
        
        # Benchmark durchführen
        results = await probe.run_benchmark(config['iterations'])
        
        # SLO-Compliance prüfen
        slo_status = probe.verify_slo_compliance(results)
        
        print("\n📊 SLO-Compliance-Status:")
        print(f"   Durchschnittslatenz: {slo_status['avg_e2e_ms']:.1f}ms")
        print(f"   Max-Latenz: {slo_status['max_e2e_ms']:.1f}ms")
        print(f"   Min-Latenz: {slo_status['min_e2e_ms']:.1f}ms")
        print(f"   Compliance-Rate: {slo_status['compliance_rate']:.1%}")
        print(f"   Latenz-SLO (< {probe.slo_target_latency}ms): {'✅' if slo_status['latency_compliant'] else '❌'}")
        print(f"   Accuracy-SLO (> {probe.slo_accuracy:.0%}): {'✅' if slo_status['accuracy_compliant'] else '❌'}")
        print(f"   Gesamt-SLO: {'✅' if slo_status['overall_compliant'] else '❌'}")
        
        # JSON-Export
        probe.export_json(results)
        
        # Ergebnis
        if slo_status['overall_compliant']:
            print("\n🎉 Alle SLOs erreicht! Loop Closure funktioniert.")
            return 0
        else:
            print("\n⚠️ SLO-Verstöße erkannt! Optimierung erforderlich.")
            return 1
            
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return 1
        
    finally:
        await probe.cleanup()

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
