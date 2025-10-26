"""
TOM v3.0 - Vereinfachter Hybrid Server
Demonstriert beide Wege: Modulare Pipeline + Direkte Speech-to-Speech
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol

# Lokale Services
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from apps.realtime.llm_ollama import llm_streamer  
from apps.realtime.tts_piper import tts_streamer
from apps.realtime.config import RealtimeConfig, RealtimeMode, get_config_summary

logger = logging.getLogger(__name__)

class HybridRealtimeServer:
    """Hybrid Server mit beiden Modi"""
    
    def __init__(self):
        self.active_connections = set()
        self.pipeline_mode = "modular"  # "modular" oder "direct"
        
    async def handle_client(self, websocket: WebSocketServerProtocol):
        logger.info(f'Client connected: {websocket.remote_address}')
        
        self.active_connections.add(websocket)
        
        try:
            await websocket.send(json.dumps({
                'type': 'connected',
                'timestamp': datetime.now().isoformat(),
                'config': get_config_summary(),
                'pipeline_mode': self.pipeline_mode,
                'message': f'Hybrid Server - {self.pipeline_mode.title()} Pipeline aktiv'
            }))
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    logger.info(f'Received: {data.get("type", "unknown")}')
                    
                    if data.get('type') == 'audio_chunk':
                        if self.pipeline_mode == "modular":
                            await self._process_modular_pipeline(websocket, data)
                        else:
                            await self._process_direct_speech_to_speech(websocket, data)
                    
                    elif data.get('type') == 'switch_mode':
                        new_mode = data.get('mode', 'modular')
                        if new_mode in ['modular', 'direct']:
                            self.pipeline_mode = new_mode
                            await websocket.send(json.dumps({
                                'type': 'mode_switched',
                                'mode': self.pipeline_mode,
                                'timestamp': datetime.now().isoformat()
                            }))
                            logger.info(f'Pipeline-Modus gewechselt zu: {self.pipeline_mode}')
                    
                except json.JSONDecodeError as e:
                    logger.error(f'JSON Error: {e}')
                except Exception as e:
                    logger.error(f'Message Error: {e}')
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f'Client disconnected: {websocket.remote_address}')
        except Exception as e:
            logger.error(f'Connection Error: {e}')
        finally:
            self.active_connections.discard(websocket)
    
    async def _process_modular_pipeline(self, websocket, data):
        """Modulare Pipeline: STT → LLM → TTS"""
        logger.info("🔄 Modulare Pipeline gestartet")
        
        try:
            # 1. STT-Verarbeitung (Mock für Demo)
            await asyncio.sleep(0.2)
            stt_text = "Hallo! Das ist eine Demonstration der modularen Pipeline."
            await websocket.send(json.dumps({
                'type': 'stt_final',
                'text': stt_text,
                'confidence': 0.95,
                'provider': 'mock_stt',
                'timestamp': datetime.now().isoformat(),
                'pipeline_step': 'stt'
            }))
            logger.info(f'STT: {stt_text}')
            
            # 2. LLM-Verarbeitung (echt mit Ollama)
            if RealtimeConfig.REALTIME_LLM == RealtimeMode.LOCAL and llm_streamer.client:
                full_llm_response = []
                async for token in llm_streamer.stream_chat_response(f"Antworte kurz auf Deutsch: {stt_text}"):
                    full_llm_response.append(token)
                    await websocket.send(json.dumps({
                        'type': 'llm_token',
                        'text': token,
                        'provider': 'ollama',
                        'model': 'qwen3:14b',
                        'timestamp': datetime.now().isoformat(),
                        'pipeline_step': 'llm'
                    }))
                    await asyncio.sleep(0.05)
                llm_response_text = "".join(full_llm_response)
            else:
                raise Exception("Ollama nicht verfügbar")
            logger.info(f'LLM: {llm_response_text[:50]}...')
            
            # 3. TTS-Verarbeitung (echt mit Piper)
            if RealtimeConfig.REALTIME_TTS == RealtimeMode.LOCAL and tts_streamer.voice:
                async for audio_chunk in tts_streamer.stream_tts_audio(llm_response_text):
                    await websocket.send(json.dumps({
                        'type': 'tts_audio',
                        'audio': audio_chunk.decode('latin1') if isinstance(audio_chunk, bytes) else str(audio_chunk),
                        'provider': 'piper',
                        'voice': 'de_DE-thorsten-medium',
                        'timestamp': datetime.now().isoformat(),
                        'pipeline_step': 'tts'
                    }))
                    await asyncio.sleep(0.05)
            else:
                raise Exception("Piper nicht verfügbar")
            logger.info('TTS: Audio gesendet')
            
            # Pipeline beendet
            await websocket.send(json.dumps({
                'type': 'pipeline_complete',
                'mode': 'modular',
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'stt_text': stt_text,
                    'llm_response': llm_response_text,
                    'tts_provider': 'piper' if RealtimeConfig.REALTIME_TTS == RealtimeMode.LOCAL else 'mock'
                }
            }))
            logger.info("✅ Modulare Pipeline abgeschlossen")
            
        except Exception as e:
            logger.error(f"Pipeline-Fehler: {e}")
            await websocket.send(json.dumps({
                'type': 'pipeline_error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }))
    
    async def _process_direct_speech_to_speech(self, websocket, data):
        """Direkte Speech-to-Speech Pipeline"""
        logger.info("⚡ Direkte Speech-to-Speech Pipeline gestartet")
        
        try:
            # Simuliere direkte Verarbeitung (für Demo)
            await asyncio.sleep(0.1)  # Sehr niedrige Latenz
            
            # Direkte Antwort ohne Zwischenschritte
            direct_response = "Das ist eine direkte Speech-to-Speech Antwort mit minimaler Latenz!"
            
            await websocket.send(json.dumps({
                'type': 'direct_response',
                'text': direct_response,
                'audio': 'direct_audio_data',
                'provider': 'direct_s2s',
                'latency_ms': 100,
                'timestamp': datetime.now().isoformat()
            }))
            
            logger.info("⚡ Direkte Speech-to-Speech abgeschlossen")
            
        except Exception as e:
            logger.error(f"Direct S2S Fehler: {e}")
            await websocket.send(json.dumps({
                'type': 'pipeline_error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }))

async def main():
    """Hauptfunktion"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    server = HybridRealtimeServer()
    
    logger.info("🚀 Starte Hybrid Realtime Server...")
    logger.info("📊 Konfiguration:", get_config_summary())
    logger.info("🔄 Modi: modular (STT→LLM→TTS) + direct (Speech-to-Speech)")
    logger.info("🌐 Server läuft auf ws://localhost:8080")
    
    start_server = websockets.serve(server.handle_client, 'localhost', 8080)
    await start_server
    await asyncio.Future()  # Run forever

if __name__ == '__main__':
    asyncio.run(main())
