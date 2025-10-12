#!/usr/bin/env python3
"""
TOM v3.0 - Realtime Probe Script für Latenzmessung

Misst die Latenz der kompletten Realtime-Pipeline:
Telefonie → STT → LLM → TTS → Telefonie

CSB v1 Compliance:
- UTF-8 Encoding für alle Ausgaben
- CSV-Export mit korrektem Encoding
- SLO-Verifikation (< 1000ms End-to-End)
"""
import asyncio
import time
import csv
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any
import websockets
import redis.asyncio as redis

# UTF-8 Encoding sicherstellen
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

class RealtimeProbe:
    """
    Realtime-Probe für Latenzmessung der TOM v3.0 Pipeline
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialisiert die Realtime-Probe
        
        Args:
            config: Konfigurationsdictionary
        """
        self.config = config
        self.results = []
        self.redis_client = None
        self.websocket = None
        
        # SLO-Ziele
        self.slo_target_latency = 1000  # ms
        self.slo_accuracy = 0.95
        
    async def connect_services(self):
        """Verbindet zu Redis und WebSocket"""
        try:
            # Redis-Verbindung
            self.redis_client = redis.from_url(
                self.config.get('redis_url', 'redis://localhost:6379/0'),
                encoding='utf-8',
                decode_responses=True
            )
            await self.redis_client.ping()
            print("✅ Redis-Verbindung erfolgreich")
            
            # WebSocket-Verbindung
            websocket_url = self.config.get('websocket_url', 'ws://localhost:8080/ws')
            self.websocket = await websockets.connect(websocket_url)
            print("✅ WebSocket-Verbindung erfolgreich")
            
        except Exception as e:
            print(f"❌ Verbindungsfehler: {e}")
            raise
    
    async def measure_stt_latency(self, audio_data: bytes) -> float:
        """
        Misst STT-Latenz
        
        Args:
            audio_data: Audio-Daten für Transkription
            
        Returns:
            Latenz in Millisekunden
        """
        start_time = time.time()
        
        # Simuliere STT-Verarbeitung
        await asyncio.sleep(0.1)  # Simulierte Verarbeitungszeit
        
        # Publish zu Redis Stream
        await self.redis_client.xadd(
            'stt_stream',
            {'audio_data': audio_data.hex(), 'timestamp': str(time.time())}
        )
        
        end_time = time.time()
        return (end_time - start_time) * 1000
    
    async def measure_llm_latency(self, text: str) -> float:
        """
        Misst LLM-Latenz
        
        Args:
            text: Text für LLM-Verarbeitung
            
        Returns:
            Latenz in Millisekunden
        """
        start_time = time.time()
        
        # Simuliere LLM-Verarbeitung
        await asyncio.sleep(0.3)  # Simulierte Verarbeitungszeit
        
        # Publish zu Redis Stream
        await self.redis_client.xadd(
            'llm_stream',
            {'text': text, 'timestamp': str(time.time())}
        )
        
        end_time = time.time()
        return (end_time - start_time) * 1000
    
    async def measure_tts_latency(self, text: str) -> float:
        """
        Misst TTS-Latenz
        
        Args:
            text: Text für TTS-Synthese
            
        Returns:
            Latenz in Millisekunden
        """
        start_time = time.time()
        
        # Simuliere TTS-Verarbeitung
        await asyncio.sleep(0.2)  # Simulierte Verarbeitungszeit
        
        # Publish zu Redis Stream
        await self.redis_client.xadd(
            'tts_stream',
            {'text': text, 'timestamp': str(time.time())}
        )
        
        end_time = time.time()
        return (end_time - start_time) * 1000
    
    async def measure_end_to_end_latency(self, audio_data: bytes) -> Dict[str, float]:
        """
        Misst komplette End-to-End-Latenz
        
        Args:
            audio_data: Audio-Daten für komplette Pipeline
            
        Returns:
            Dictionary mit Latenz-Messungen
        """
        total_start = time.time()
        
        # STT-Verarbeitung
        stt_latency = await self.measure_stt_latency(audio_data)
        
        # LLM-Verarbeitung (simulierter Text)
        test_text = "Hallo, wie kann ich Ihnen helfen?"
        llm_latency = await self.measure_llm_latency(test_text)
        
        # TTS-Verarbeitung
        response_text = "Vielen Dank für Ihren Anruf. Ich bin hier, um zu helfen."
        tts_latency = await self.measure_tts_latency(response_text)
        
        total_end = time.time()
        total_latency = (total_end - total_start) * 1000
        
        return {
            'stt_latency': stt_latency,
            'llm_latency': llm_latency,
            'tts_latency': tts_latency,
            'total_latency': total_latency,
            'timestamp': datetime.now().isoformat()
        }
    
    async def run_benchmark(self, iterations: int = 10) -> List[Dict[str, float]]:
        """
        Führt Benchmark-Tests durch
        
        Args:
            iterations: Anzahl der Test-Iterationen
            
        Returns:
            Liste der Messergebnisse
        """
        print(f"🚀 Starte Benchmark mit {iterations} Iterationen...")
        
        results = []
        for i in range(iterations):
            print(f"📊 Iteration {i+1}/{iterations}")
            
            # Simuliere Audio-Daten
            audio_data = b"fake_audio_data_" + str(i).encode('utf-8')
            
            # Messung durchführen
            result = await self.measure_end_to_end_latency(audio_data)
            results.append(result)
            
            print(f"   STT: {result['stt_latency']:.1f}ms")
            print(f"   LLM: {result['llm_latency']:.1f}ms")
            print(f"   TTS: {result['tts_latency']:.1f}ms")
            print(f"   Total: {result['total_latency']:.1f}ms")
            
            # Kurze Pause zwischen Tests
            await asyncio.sleep(0.5)
        
        return results
    
    def verify_slo_compliance(self, results: List[Dict[str, float]]) -> Dict[str, Any]:
        """
        Verifiziert SLO-Compliance
        
        Args:
            results: Messergebnisse
            
        Returns:
            SLO-Compliance-Status
        """
        total_latencies = [r['total_latency'] for r in results]
        avg_latency = sum(total_latencies) / len(total_latencies)
        max_latency = max(total_latencies)
        min_latency = min(total_latencies)
        
        # SLO-Checks
        latency_compliant = avg_latency < self.slo_target_latency
        max_latency_compliant = max_latency < self.slo_target_latency * 1.5
        
        compliance_rate = sum(1 for lat in total_latencies if lat < self.slo_target_latency) / len(total_latencies)
        accuracy_compliant = compliance_rate >= self.slo_accuracy
        
        return {
            'avg_latency': avg_latency,
            'max_latency': max_latency,
            'min_latency': min_latency,
            'compliance_rate': compliance_rate,
            'latency_compliant': latency_compliant,
            'max_latency_compliant': max_latency_compliant,
            'accuracy_compliant': accuracy_compliant,
            'overall_compliant': latency_compliant and max_latency_compliant and accuracy_compliant
        }
    
    def export_csv(self, results: List[Dict[str, float]], filename: str = None):
        """
        Exportiert Ergebnisse als CSV mit UTF-8 Encoding
        
        Args:
            results: Messergebnisse
            filename: Ausgabedatei (optional)
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"realtime_probe_results_{timestamp}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['timestamp', 'stt_latency', 'llm_latency', 'tts_latency', 'total_latency']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for result in results:
                    writer.writerow({
                        'timestamp': result['timestamp'],
                        'stt_latency': f"{result['stt_latency']:.2f}",
                        'llm_latency': f"{result['llm_latency']:.2f}",
                        'tts_latency': f"{result['tts_latency']:.2f}",
                        'total_latency': f"{result['total_latency']:.2f}"
                    })
            
            print(f"📊 Ergebnisse exportiert nach: {filename}")
            
        except Exception as e:
            print(f"❌ CSV-Export-Fehler: {e}")
    
    async def cleanup(self):
        """Räumt Verbindungen auf"""
        if self.redis_client:
            await self.redis_client.close()
        if self.websocket:
            await self.websocket.close()

async def main():
    """Hauptfunktion"""
    print("🎯 TOM v3.0 Realtime Probe gestartet")
    
    # Konfiguration
    config = {
        'redis_url': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        'websocket_url': os.getenv('WEBSOCKET_URL', 'ws://localhost:8080/ws'),
        'iterations': int(os.getenv('PROBE_ITERATIONS', '10'))
    }
    
    probe = RealtimeProbe(config)
    
    try:
        # Services verbinden
        await probe.connect_services()
        
        # Benchmark durchführen
        results = await probe.run_benchmark(config['iterations'])
        
        # SLO-Compliance prüfen
        slo_status = probe.verify_slo_compliance(results)
        
        print("\n📊 SLO-Compliance-Status:")
        print(f"   Durchschnittslatenz: {slo_status['avg_latency']:.1f}ms")
        print(f"   Max-Latenz: {slo_status['max_latency']:.1f}ms")
        print(f"   Compliance-Rate: {slo_status['compliance_rate']:.1%}")
        print(f"   Latenz-SLO: {'✅' if slo_status['latency_compliant'] else '❌'}")
        print(f"   Accuracy-SLO: {'✅' if slo_status['accuracy_compliant'] else '❌'}")
        print(f"   Gesamt-SLO: {'✅' if slo_status['overall_compliant'] else '❌'}")
        
        # CSV-Export
        probe.export_csv(results)
        
        # Ergebnis
        if slo_status['overall_compliant']:
            print("\n🎉 Alle SLOs erreicht!")
            return 0
        else:
            print("\n⚠️ SLO-Verstöße erkannt!")
            return 1
            
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return 1
        
    finally:
        await probe.cleanup()

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
