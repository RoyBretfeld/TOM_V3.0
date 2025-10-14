"""
TOM v3.0 - Hybrid Realtime Server
Kombiniert Mock + lokale GPU-beschleunigte Services
"""

import asyncio
import json
import logging
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol

# Lokale Services
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from apps.realtime.stt_whisperx import stt_streamer
from apps.realtime.llm_ollama import llm_streamer  
from apps.realtime.tts_piper import tts_streamer
from apps.realtime.config import get_config_summary

logger = logging.getLogger(__name__)


class HybridRealtimeServer:
    """Hybrid-Server mit Mock + lokalen Services"""
    
    def __init__(self):
        self.active_connections = set()
        self.config = get_config_summary()
        
    async def handle_client(self, websocket: WebSocketServerProtocol):
        """Behandelt WebSocket-Verbindungen"""
        client_addr = websocket.remote_address
        logger.info(f"Client verbunden: {client_addr}")
        
        self.active_connections.add(websocket)
        
        try:
            # Willkommensnachricht mit Konfiguration
            await websocket.send(json.dumps({
                'type': 'connected',
                'timestamp': datetime.now().isoformat(),
                'config': self.config,
                'message': 'Hybrid Realtime Server bereit'
            }))
            
            # Nachrichten verarbeiten
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(websocket, data)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON-Fehler von {client_addr}: {e}")
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'error': 'Ungültiges JSON',
                        'timestamp': datetime.now().isoformat()
                    }))
                except Exception as e:
                    logger.error(f"Nachrichten-Fehler von {client_addr}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client getrennt: {client_addr}")
        except Exception as e:
            logger.error(f"Verbindungsfehler {client_addr}: {e}")
        finally:
            self.active_connections.discard(websocket)
    
    async def _process_message(self, websocket: WebSocketServerProtocol, data: dict):
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
    
    async def _process_audio_chunk(self, websocket: WebSocketServerProtocol, data: dict):
        """Verarbeitet Audio-Chunk durch die Pipeline"""
        try:
            audio_data = data.get('audio', '')
            
            # STT-Verarbeitung
            logger.info("STT-Verarbeitung...")
            async for stt_event in stt_streamer.process_audio_chunk(audio_data):
                await websocket.send(json.dumps(stt_event))
                
                # Wenn STT erfolgreich, weiter zu LLM
                if stt_event.get('type') == 'stt_final' and stt_event.get('text'):
                    text = stt_event['text']
                    logger.info(f"STT-Ergebnis: {text}")
                    
                    # LLM-Verarbeitung
                    logger.info("LLM-Verarbeitung...")
                    async for llm_event in llm_streamer.process_text(text):
                        await websocket.send(json.dumps(llm_event))
                        
                        # Wenn LLM-Token empfangen, weiter zu TTS
                        if llm_event.get('type') == 'llm_token' and llm_event.get('text'):
                            tts_text = llm_event['text']
                            
                            # TTS-Verarbeitung
                            logger.info("TTS-Verarbeitung...")
                            async for tts_event in tts_streamer.process_text(tts_text):
                                await websocket.send(json.dumps(tts_event))
                    
                    # Turn beendet
                    await websocket.send(json.dumps({
                        'type': 'turn_end',
                        'timestamp': datetime.now().isoformat(),
                        'pipeline': 'hybrid'
                    }))
                    
                    logger.info("Turn abgeschlossen")
                    break
                    
        except Exception as e:
            logger.error(f"Audio-Verarbeitung fehlgeschlagen: {e}")
            await websocket.send(json.dumps({
                'type': 'pipeline_error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }))
    
    async def start_server(self, host: str = "localhost", port: int = 8080):
        """Startet den Hybrid-Server"""
        logger.info("Starte Hybrid Realtime Server...")
        logger.info(f"Konfiguration: {self.config}")
        
        start_server = websockets.serve(
            self.handle_client,
            host,
            port
        )
        
        logger.info(f"Server läuft auf ws://{host}:{port}")
        await start_server


async def main():
    """Hauptfunktion"""
    # Logging konfigurieren
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Server starten
    server = HybridRealtimeServer()
    await server.start_server()
    
    # Server laufen lassen
    await asyncio.Future()  # Läuft für immer


if __name__ == '__main__':
    asyncio.run(main())
