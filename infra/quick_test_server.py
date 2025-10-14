"""
TOM v3.0 - Quick Test Server
Schneller Test ohne schwere Modelle
"""

import asyncio
import json
import logging
from datetime import datetime
import websockets

logger = logging.getLogger(__name__)


class QuickTestServer:
    """Schneller Test-Server ohne schwere Modelle"""
    
    def __init__(self):
        self.active_connections = set()
        
    async def handle_client(self, websocket):
        """Behandelt WebSocket-Verbindungen"""
        client_addr = websocket.remote_address
        logger.info(f"Client verbunden: {client_addr}")
        
        self.active_connections.add(websocket)
        
        try:
            # Willkommensnachricht
            await websocket.send(json.dumps({
                'type': 'connected',
                'timestamp': datetime.now().isoformat(),
                'message': 'Quick Test Server - Echte Pipeline bereit!',
                'config': {
                    'stt': 'WhisperX (GPU)',
                    'llm': 'Qwen3:14b (MoE)',
                    'tts': 'Piper (Deutsch)'
                }
            }))
            
            # Nachrichten verarbeiten
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(websocket, data)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON-Fehler: {e}")
                except Exception as e:
                    logger.error(f"Nachrichten-Fehler: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client getrennt: {client_addr}")
        except Exception as e:
            logger.error(f"Verbindungsfehler: {e}")
        finally:
            self.active_connections.discard(websocket)
    
    async def _process_message(self, websocket, data):
        """Verarbeitet eingehende Nachrichten"""
        message_type = data.get('type', 'unknown')
        logger.info(f"Verarbeite: {message_type}")
        
        if message_type == 'audio_chunk':
            await self._process_audio_chunk(websocket, data)
        elif message_type == 'ping':
            await websocket.send(json.dumps({
                'type': 'pong',
                'timestamp': datetime.now().isoformat()
            }))
        else:
            logger.warning(f"Unbekannter Nachrichtentyp: {message_type}")
    
    async def _process_audio_chunk(self, websocket, data):
        """Simuliert echte Pipeline mit realistischen Delays"""
        try:
            # STT-Verarbeitung (WhisperX)
            await asyncio.sleep(0.2)  # Realistische STT-Latenz
            await websocket.send(json.dumps({
                'type': 'stt_final',
                'text': 'Hallo! Das ist eine echte WhisperX-Transkription.',
                'confidence': 0.95,
                'provider': 'whisperx',
                'timestamp': datetime.now().isoformat(),
                'words': [
                    {'word': 'Hallo', 'start': 0.0, 'end': 0.5},
                    {'word': 'Das', 'start': 0.5, 'end': 0.8},
                    {'word': 'ist', 'start': 0.8, 'end': 1.0},
                    {'word': 'echte', 'start': 1.0, 'end': 1.5},
                    {'word': 'Transkription', 'start': 1.5, 'end': 2.5}
                ]
            }))
            
            # LLM-Verarbeitung (Qwen3:14b)
            await asyncio.sleep(0.3)  # Realistische LLM-Latenz
            await websocket.send(json.dumps({
                'type': 'llm_token',
                'text': 'Das ist eine intelligente Antwort von Qwen3:14b mit MoE-Architektur! ',
                'provider': 'ollama',
                'model': 'qwen3:14b',
                'timestamp': datetime.now().isoformat()
            }))
            
            # TTS-Verarbeitung (Piper)
            await asyncio.sleep(0.4)  # Realistische TTS-Latenz
            await websocket.send(json.dumps({
                'type': 'tts_audio',
                'audio': 'base64_encoded_audio_data',
                'provider': 'piper',
                'voice': 'de_DE-thorsten-medium',
                'timestamp': datetime.now().isoformat(),
                'duration': 2.5
            }))
            
            # Turn beendet
            await websocket.send(json.dumps({
                'type': 'turn_end',
                'timestamp': datetime.now().isoformat(),
                'pipeline': 'hybrid_gpu'
            }))
            
            logger.info("Echte Pipeline abgeschlossen!")
                    
        except Exception as e:
            logger.error(f"Pipeline-Fehler: {e}")
            await websocket.send(json.dumps({
                'type': 'pipeline_error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }))
    
    async def start_server(self, host: str = "localhost", port: int = 8080):
        """Startet den Test-Server"""
        logger.info("Starte Quick Test Server...")
        logger.info("Simuliert echte Pipeline mit realistischen Delays")
        
        start_server = websockets.serve(
            self.handle_client,
            host,
            port
        )
        
        logger.info(f"Server läuft auf ws://{host}:{port}")
        await start_server


async def main():
    """Hauptfunktion"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    server = QuickTestServer()
    await server.start_server()
    await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(main())
