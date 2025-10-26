#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOM v3.0 - Einfacher Realtime Server (ohne komplexe Dependencies)
Funktioniert sofort!
"""

import asyncio
import json
import logging
import time
import websockets
from datetime import datetime

logger = logging.getLogger(__name__)

class SimpleRealtimeServer:
    """Einfacher Realtime-Server ohne komplexe Dependencies"""
    
    def __init__(self):
        self.active_connections = set()
        
    async def handle_client(self, websocket, path):
        """Client-Handler"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f'Client verbunden: {client_id}')
        
        self.active_connections.add(websocket)
        
        try:
            # Connected-Event senden
            await websocket.send(json.dumps({
                'type': 'connected',
                'call_id': 'simple-call-001',
                'timestamp': datetime.now().isoformat(),
                'message': 'Einfacher Server läuft!'
            }))
            
            # Event-Loop
            async for message in websocket:
                try:
                    data = json.loads(message)
                    logger.info(f'Empfangen: {data.get("type", "unknown")}')
                    
                    # Audio-Chunk verarbeiten
                    if data.get('type') == 'audio_chunk':
                        await self.process_audio_chunk(websocket, data)
                    
                    # Ping verarbeiten
                    elif data.get('type') == 'ping':
                        await websocket.send(json.dumps({
                            'type': 'pong',
                            'timestamp': datetime.now().isoformat(),
                            'latency_ms': 50  # Simulierte Latenz
                        }))
                    
                    # Barge-In verarbeiten
                    elif data.get('type') == 'barge_in':
                        await websocket.send(json.dumps({
                            'type': 'barge_in_ack',
                            'timestamp': datetime.now().isoformat()
                        }))
                    
                except json.JSONDecodeError as e:
                    logger.warning(f'JSON Fehler: {e}')
                except Exception as e:
                    logger.error(f'Nachrichten-Fehler: {e}')
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f'Client getrennt: {client_id}')
        except Exception as e:
            logger.error(f'Verbindungs-Fehler: {e}')
        finally:
            self.active_connections.discard(websocket)
    
    async def process_audio_chunk(self, websocket, data):
        """Audio-Chunk verarbeiten (simuliert)"""
        logger.info(f'Audio-Chunk empfangen: {data.get("audio_length", 0)} bytes')
        
        # Simuliere STT-Verarbeitung
        await asyncio.sleep(0.2)  # 200ms STT-Simulation
        
        await websocket.send(json.dumps({
            'type': 'stt_final',
            'text': 'Hallo! Das ist eine simulierte Antwort.',
            'confidence': 0.95,
            'timestamp': datetime.now().isoformat(),
            'provider': 'simple_server'
        }))
        
        # Simuliere LLM-Verarbeitung
        await asyncio.sleep(0.3)  # 300ms LLM-Simulation
        
        await websocket.send(json.dumps({
            'type': 'llm_complete',
            'text': 'Das ist eine simulierte LLM-Antwort vom einfachen Server.',
            'timestamp': datetime.now().isoformat(),
            'provider': 'simple_server'
        }))
        
        # Simuliere TTS-Verarbeitung
        await asyncio.sleep(0.1)  # 100ms TTS-Simulation
        
        await websocket.send(json.dumps({
            'type': 'tts_complete',
            'message': 'TTS-Verarbeitung abgeschlossen',
            'timestamp': datetime.now().isoformat(),
            'provider': 'simple_server'
        }))
        
        logger.info('Audio-Pipeline abgeschlossen')

async def main():
    """Hauptfunktion"""
    server = SimpleRealtimeServer()
    
    logger.info('🚀 Starte einfachen Realtime-Server...')
    logger.info('📡 URL: ws://localhost:8081/')
    
    # WebSocket Server starten
    start_server = websockets.serve(
        server.handle_client, 
        'localhost', 
        8081
    )
    
    await start_server
    logger.info('✅ Server läuft auf ws://localhost:8081/')
    
    # Forever loop
    await asyncio.Future()

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
